"""老师（导师）端：只看/只评填报了自己志愿的学生。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models
from ..core.database import get_db
from ..core.deps import client_ip, ensure_in_window, get_current_mentor, write_audit
from ..core.errors import AppError, ErrorCode
from ..core.response import ok
from ..schemas import TeacherInterviewIn
from ..services import selection_service as service
from ..services.selection import Interview as DomainInterview

router = APIRouter(prefix='/teacher', tags=['teacher'])


def _mentor_of(db: Session, user: models.User) -> models.Mentor:
    mentor = db.get(models.Mentor, user.mentor_id)
    if not mentor:
        raise AppError(ErrorCode.NOT_FOUND, '导师档案不存在')
    return mentor


def _interview_view(row: models.Interview | None) -> dict | None:
    if not row:
        return None
    total = DomainInterview(
        row.student_id,
        row.mentor_id,
        row.score_attitude,
        row.score_logic,
        row.score_code,
        row.score_time,
    ).total
    return {
        'id': row.id,
        'round_id': row.round_id,
        'score_attitude': row.score_attitude,
        'score_logic': row.score_logic,
        'score_code': row.score_code,
        'score_time': row.score_time,
        'total_score': total,
        'decision': row.decision,
        'remark': row.remark,
        'updated_at': row.updated_at,
    }


def _offer_view(row: models.Offer | None) -> dict | None:
    if not row:
        return None
    return {
        'id': row.id,
        'round_id': row.round_id,
        'offer_type': row.offer_type,
        'status': row.status,
        'reason': row.reason,
        'created_at': row.created_at,
        'expires_at': row.expires_at,
        'confirmed_at': row.confirmed_at,
    }


@router.get('/profile')
def profile(
    user: models.User = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = _mentor_of(db, user)
    lab = db.get(models.Lab, mentor.lab_id)
    quota_left = service.remaining_quota(db, mentor)
    applicant_ids = {
        row[0]
        for row in db.query(models.Intention.student_id)
        .filter(models.Intention.mentor_id == mentor.id)
        .all()
    }
    interviewed = (
        db.query(models.Interview.student_id)
        .filter(models.Interview.mentor_id == mentor.id)
        .distinct()
        .count()
    )
    offers = db.query(models.Offer).filter(models.Offer.mentor_id == mentor.id).all()
    return ok(
        {
            'mentor': {
                'id': mentor.id,
                'name': mentor.name,
                'quota': mentor.quota,
                'requirement': mentor.requirement,
                'is_active': mentor.is_active,
            },
            'lab': (
                {
                    'id': lab.id,
                    'name': lab.name,
                    'capacity': lab.capacity,
                    'direction': lab.direction,
                }
                if lab
                else None
            ),
            'quota_left': quota_left,
            'quota_taken': mentor.quota - quota_left,
            'counts': {
                'applicants': len(applicant_ids),
                'interviewed': interviewed,
                'offers_pending': sum(
                    1 for row in offers if row.status == models.OfferStatus.pending
                ),
                'offers_confirmed': sum(
                    1 for row in offers if row.status == models.OfferStatus.confirmed
                ),
            },
        }
    )


@router.get('/applicants')
def applicants(
    user: models.User = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = _mentor_of(db, user)
    rows = (
        db.query(models.Intention)
        .filter(models.Intention.mentor_id == mentor.id)
        .order_by(models.Intention.round_id.desc(), models.Intention.priority)
        .all()
    )
    items = []
    seen: set[int] = set()
    for row in rows:
        if row.student_id in seen:
            continue
        seen.add(row.student_id)
        student = db.get(models.User, row.student_id)
        if not student:
            continue
        interview = (
            db.query(models.Interview)
            .filter(
                models.Interview.student_id == student.id,
                models.Interview.mentor_id == mentor.id,
            )
            .order_by(models.Interview.round_id.desc(), models.Interview.id.desc())
            .first()
        )
        offer = (
            db.query(models.Offer)
            .filter(
                models.Offer.student_id == student.id,
                models.Offer.mentor_id == mentor.id,
            )
            .order_by(models.Offer.id.desc())
            .first()
        )
        items.append(
            {
                'student_id': student.id,
                'student_no': student.student_no,
                'student_name': student.name,
                'obey_internal': student.obey_internal,
                'obey_cross': student.obey_cross,
                'intention_round_id': row.round_id,
                'priority': row.priority,
                'intended_at': row.created_at,
                'interview': _interview_view(interview),
                'offer': _offer_view(offer),
            }
        )
    return ok(items)


@router.get('/interviews')
def list_interviews(
    round_id: int | None = None,
    user: models.User = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = _mentor_of(db, user)
    query = db.query(models.Interview).filter(models.Interview.mentor_id == mentor.id)
    if round_id:
        query = query.filter(models.Interview.round_id == round_id)
    items = []
    for row in query.order_by(models.Interview.round_id.desc(), models.Interview.id.desc()).all():
        student = db.get(models.User, row.student_id)
        items.append(
            {
                'id': row.id,
                'student_id': row.student_id,
                'student_no': student.student_no if student else '',
                'student_name': student.name if student else '',
                'mentor_id': row.mentor_id,
                'round_id': row.round_id,
                **_interview_view(row),
            }
        )
    return ok(items)


@router.post('/interviews')
def upsert_interview(
    payload: TeacherInterviewIn,
    request: Request,
    user: models.User = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = _mentor_of(db, user)
    student = db.get(models.User, payload.student_id)
    if not student or student.role != models.Role.student:
        raise AppError(ErrorCode.NOT_FOUND, '学生不存在')

    applied = (
        db.query(models.Intention)
        .filter(
            models.Intention.student_id == student.id,
            models.Intention.mentor_id == mentor.id,
        )
        .first()
    )
    if not applied:
        raise AppError(ErrorCode.FORBIDDEN, '该学生未填报你的志愿，不能评分')

    ensure_in_window(db, payload.round_id, action='面试评分')

    domain = DomainInterview(
        payload.student_id,
        mentor.id,
        payload.score_attitude,
        payload.score_logic,
        payload.score_code,
        payload.score_time,
    )

    row = (
        db.query(models.Interview)
        .filter(
            models.Interview.student_id == student.id,
            models.Interview.mentor_id == mentor.id,
            models.Interview.round_id == payload.round_id,
        )
        .first()
    )
    before = None
    if row:
        before = {
            'score_attitude': row.score_attitude,
            'score_logic': row.score_logic,
            'score_code': row.score_code,
            'score_time': row.score_time,
        }
        row.score_attitude = payload.score_attitude
        row.score_logic = payload.score_logic
        row.score_code = payload.score_code
        row.score_time = payload.score_time
        row.remark = payload.remark
        row.scored_by = user.id
        action = 'update_interview'
    else:
        row = models.Interview(
            student_id=student.id,
            mentor_id=mentor.id,
            round_id=payload.round_id,
            score_attitude=payload.score_attitude,
            score_logic=payload.score_logic,
            score_code=payload.score_code,
            score_time=payload.score_time,
            remark=payload.remark,
            scored_by=user.id,
        )
        db.add(row)
        action = 'create_interview'
    db.commit()
    db.refresh(row)

    write_audit(
        db,
        actor=user,
        action=action,
        entity='interview',
        entity_id=row.id,
        before=before,
        after=payload.model_dump(mode='json'),
        ip=client_ip(request),
        commit=True,
    )
    return ok({'id': row.id, 'total': domain.total})


@router.get('/offers')
def my_offers(
    round_id: int | None = None,
    status: models.OfferStatus | None = None,
    user: models.User = Depends(get_current_mentor),
    db: Session = Depends(get_db),
):
    mentor = _mentor_of(db, user)
    query = db.query(models.Offer).filter(models.Offer.mentor_id == mentor.id)
    if round_id:
        query = query.filter(models.Offer.round_id == round_id)
    if status:
        query = query.filter(models.Offer.status == status)
    items = []
    for row in query.order_by(models.Offer.id.desc()).all():
        student = db.get(models.User, row.student_id)
        lab = db.get(models.Lab, mentor.lab_id)
        items.append(
            {
                'id': row.id,
                'student_id': row.student_id,
                'student_no': student.student_no if student else '',
                'student_name': student.name if student else '',
                'mentor_id': mentor.id,
                'mentor_name': mentor.name,
                'lab_name': lab.name if lab else '',
                'round_id': row.round_id,
                **_offer_view(row),
            }
        )
    return ok(items)

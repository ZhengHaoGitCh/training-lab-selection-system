from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .. import models
from ..core.database import get_db
from ..core.clock import utcnow
from ..core.deps import (
    client_ip,
    ensure_in_window,
    require_admin,
    write_audit,
)
from ..core.errors import AppError, ErrorCode
from ..core.response import ok
from ..schemas import (
    AdjustIn,
    AssignTalkIn,
    FillVacancyIn,
    InterviewIn,
    LabIn,
    LabPatch,
    MentorIn,
    MentorPatch,
    RoundIn,
    RoundPatch,
    RunSelectionIn,
)
from ..services import selection_service as service
from ..services.selection import Interview as DomainInterview

router = APIRouter(prefix='/admin', tags=['admin'])


# ---------------- 实训室 ----------------

@router.get('/labs')
def list_labs(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    items = []
    for lab in db.query(models.Lab).order_by(models.Lab.id).all():
        mentors = [m for m in lab.mentors if m.is_active]
        items.append(
            {
                'id': lab.id,
                'name': lab.name,
                'capacity': lab.capacity,
                'direction': lab.direction,
                'description': lab.description,
                'open_day_at': lab.open_day_at,
                'mentor_count': len(mentors),
                'quota_total': sum(m.quota for m in mentors),
            }
        )
    return ok(items)


@router.post('/labs')
def create_lab(
    payload: LabIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    if db.query(models.Lab).filter(models.Lab.name == payload.name).first():
        raise AppError(ErrorCode.CONFLICT, '实训室名称已存在')
    lab = models.Lab(**payload.model_dump())
    db.add(lab)
    db.commit()
    db.refresh(lab)
    write_audit(
        db, actor=actor, action='create_lab', entity='lab', entity_id=lab.id,
        after=payload.model_dump(mode='json'), ip=client_ip(request), commit=True,
    )
    return ok({'id': lab.id})


@router.patch('/labs/{lab_id}')
def update_lab(
    lab_id: int,
    payload: LabPatch,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    lab = db.get(models.Lab, lab_id)
    if not lab:
        raise AppError(ErrorCode.NOT_FOUND, '实训室不存在')
    before = {'name': lab.name, 'capacity': lab.capacity, 'direction': lab.direction}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lab, key, value)
    db.commit()
    write_audit(
        db, actor=actor, action='update_lab', entity='lab', entity_id=lab.id,
        before=before, after=payload.model_dump(exclude_unset=True, mode='json'), commit=True,
    )
    return ok({'id': lab.id, 'name': lab.name, 'capacity': lab.capacity})


@router.delete('/labs/{lab_id}')
def delete_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    lab = db.get(models.Lab, lab_id)
    if not lab:
        raise AppError(ErrorCode.NOT_FOUND, '实训室不存在')
    if db.query(models.Intention).join(
        models.Mentor, models.Mentor.id == models.Intention.mentor_id
    ).filter(models.Mentor.lab_id == lab_id).first():
        raise AppError(ErrorCode.CONFLICT, '该实训室已有志愿记录，禁止删除')
    db.delete(lab)
    db.commit()
    write_audit(
        db, actor=actor, action='delete_lab', entity='lab', entity_id=lab_id, commit=True,
    )
    return ok({'deleted': lab_id})


# ---------------- 导师 ----------------

@router.get('/mentors')
def list_mentors(
    lab_id: int | None = None,
    keyword: str = '',
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    query = db.query(models.Mentor)
    if lab_id:
        query = query.filter(models.Mentor.lab_id == lab_id)
    if keyword:
        query = query.filter(models.Mentor.name.like(f'%{keyword}%'))
    items = []
    for mentor in query.order_by(models.Mentor.id).all():
        items.append(
            {
                'id': mentor.id,
                'lab_id': mentor.lab_id,
                'lab_name': mentor.lab.name if mentor.lab else '',
                'name': mentor.name,
                'quota': mentor.quota,
                'quota_taken': mentor.quota - service.remaining_quota(db, mentor),
                'requirement': mentor.requirement,
                'is_active': mentor.is_active,
            }
        )
    return ok(items)


@router.post('/mentors')
def create_mentor(
    payload: MentorIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    lab = db.get(models.Lab, payload.lab_id)
    if not lab:
        raise AppError(ErrorCode.NOT_FOUND, '所属实训室不存在')

    used = db.query(func.coalesce(func.sum(models.Mentor.quota), 0)).filter(
        models.Mentor.lab_id == lab.id
    ).scalar() or 0
    if lab.capacity and int(used) + payload.quota > lab.capacity:
        raise AppError(
            ErrorCode.CONFLICT,
            f'导师名额合计（{int(used) + payload.quota}）超过实训室容量（{lab.capacity}）',
        )

    mentor = models.Mentor(**payload.model_dump())
    db.add(mentor)
    db.commit()
    db.refresh(mentor)
    write_audit(
        db, actor=actor, action='create_mentor', entity='mentor', entity_id=mentor.id,
        after=payload.model_dump(mode='json'), ip=client_ip(request), commit=True,
    )
    return ok({'id': mentor.id})


@router.patch('/mentors/{mentor_id}')
def update_mentor(
    mentor_id: int,
    payload: MentorPatch,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    mentor = db.get(models.Mentor, mentor_id)
    if not mentor:
        raise AppError(ErrorCode.NOT_FOUND, '导师不存在')
    data = payload.model_dump(exclude_unset=True)
    if 'quota' in data:
        taken = mentor.quota - service.remaining_quota(db, mentor)
        if data['quota'] < taken:
            raise AppError(ErrorCode.CONFLICT, f'已有 {taken} 个名额被占用，不能低于该值')
    before = {'quota': mentor.quota, 'name': mentor.name, 'is_active': mentor.is_active}
    for key, value in data.items():
        setattr(mentor, key, value)
    db.commit()
    write_audit(
        db, actor=actor, action='update_mentor', entity='mentor', entity_id=mentor.id,
        before=before, after=data, commit=True,
    )
    return ok({'id': mentor.id, 'quota': mentor.quota, 'is_active': mentor.is_active})


@router.delete('/mentors/{mentor_id}')
def delete_mentor(
    mentor_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    mentor = db.get(models.Mentor, mentor_id)
    if not mentor:
        raise AppError(ErrorCode.NOT_FOUND, '导师不存在')
    if db.query(models.Intention).filter(models.Intention.mentor_id == mentor_id).first():
        raise AppError(ErrorCode.CONFLICT, '该导师已有志愿记录，建议置为停用而非删除')
    db.delete(mentor)
    db.commit()
    write_audit(
        db, actor=actor, action='delete_mentor', entity='mentor', entity_id=mentor_id, commit=True,
    )
    return ok({'deleted': mentor_id})


# ---------------- 轮次 ----------------

@router.get('/rounds')
def list_rounds(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    now = utcnow()
    rows = db.query(models.Round).order_by(models.Round.starts_at).all()
    return ok(
        [
            {
                'id': r.id,
                'name': r.name,
                'kind': r.kind,
                'round_no': r.round_no,
                'starts_at': r.starts_at,
                'ends_at': r.ends_at,
                'is_open': r.starts_at <= now <= r.ends_at,
            }
            for r in rows
        ]
    )


@router.post('/rounds')
def create_round(
    payload: RoundIn,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    round_obj = models.Round(**payload.model_dump())
    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)
    write_audit(
        db, actor=actor, action='create_round', entity='round', entity_id=round_obj.id,
        after=payload.model_dump(mode='json'), commit=True,
    )
    return ok({'id': round_obj.id})


@router.patch('/rounds/{round_id}')
def update_round(
    round_id: int,
    payload: RoundPatch,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    round_obj = db.get(models.Round, round_id)
    if not round_obj:
        raise AppError(ErrorCode.NOT_FOUND, '轮次不存在')
    data = payload.model_dump(exclude_unset=True)
    if data.get('starts_at') and data.get('ends_at'):
        if data['ends_at'] <= data['starts_at']:
            raise AppError(ErrorCode.PARAM, 'ends_at 必须晚于 starts_at')
    if 'starts_at' in data and 'ends_at' not in data and data['starts_at'] >= round_obj.ends_at:
        raise AppError(ErrorCode.PARAM, 'starts_at 必须早于现有 ends_at')
    if 'ends_at' in data and 'starts_at' not in data and data['ends_at'] <= round_obj.starts_at:
        raise AppError(ErrorCode.PARAM, 'ends_at 必须晚于现有 starts_at')
    before = {
        'name': round_obj.name,
        'kind': round_obj.kind.value,
        'round_no': round_obj.round_no,
        'starts_at': str(round_obj.starts_at),
        'ends_at': str(round_obj.ends_at),
    }
    for key, value in data.items():
        setattr(round_obj, key, value)
    db.commit()
    write_audit(
        db, actor=actor, action='update_round', entity='round', entity_id=round_id,
        before=before, after=payload.model_dump(exclude_unset=True, mode='json'), commit=True,
    )
    return ok({'id': round_id, 'name': round_obj.name, 'kind': round_obj.kind.value,
               'round_no': round_obj.round_no})


# ---------------- 面试与选拔 ----------------

@router.post('/interviews')
def upsert_interview(
    payload: InterviewIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    student = db.get(models.User, payload.student_id)
    mentor = db.get(models.Mentor, payload.mentor_id)
    if not student or student.role != models.Role.student:
        raise AppError(ErrorCode.NOT_FOUND, '学生不存在')
    if not mentor:
        raise AppError(ErrorCode.NOT_FOUND, '导师不存在')
    ensure_in_window(db, payload.round_id, action='面试评分')

    domain = DomainInterview(
        payload.student_id,
        payload.mentor_id,
        payload.score_attitude,
        payload.score_logic,
        payload.score_code,
        payload.score_time,
    )

    row = (
        db.query(models.Interview)
        .filter(
            models.Interview.student_id == payload.student_id,
            models.Interview.mentor_id == payload.mentor_id,
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
        row.scored_by = actor.id
        action = 'update_interview'
    else:
        row = models.Interview(
            student_id=payload.student_id,
            mentor_id=payload.mentor_id,
            round_id=payload.round_id,
            score_attitude=payload.score_attitude,
            score_logic=payload.score_logic,
            score_code=payload.score_code,
            score_time=payload.score_time,
            remark=payload.remark,
            scored_by=actor.id,
        )
        db.add(row)
        action = 'create_interview'
    db.commit()
    db.refresh(row)

    write_audit(
        db, actor=actor, action=action, entity='interview', entity_id=row.id,
        before=before, after=payload.model_dump(mode='json'), ip=client_ip(request), commit=True,
    )
    return ok({'id': row.id, 'total': domain.total})


@router.get('/interviews')
def list_interviews(
    round_id: int | None = None,
    mentor_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    query = db.query(models.Interview)
    if round_id:
        query = query.filter(models.Interview.round_id == round_id)
    if mentor_id:
        query = query.filter(models.Interview.mentor_id == mentor_id)
    total = query.count()
    rows = query.order_by(models.Interview.id).limit(limit).offset(offset).all()

    items = []
    for row in rows:
        student = db.get(models.User, row.student_id)
        mentor = db.get(models.Mentor, row.mentor_id)
        items.append(
            {
                'id': row.id,
                'student_id': row.student_id,
                'student_no': student.student_no if student else '',
                'student_name': student.name if student else '',
                'mentor_id': row.mentor_id,
                'mentor_name': mentor.name if mentor else '',
                'round_id': row.round_id,
                'score_attitude': row.score_attitude,
                'score_logic': row.score_logic,
                'score_code': row.score_code,
                'score_time': row.score_time,
                'total_score': DomainInterview(
                    row.student_id,
                    row.mentor_id,
                    row.score_attitude,
                    row.score_logic,
                    row.score_code,
                    row.score_time,
                ).total,
                'decision': row.decision,
                'remark': row.remark,
            }
        )
    return ok({'total': total, 'limit': limit, 'offset': offset, 'items': items})


@router.post('/run-selection')
def run_selection(
    payload: RunSelectionIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    ensure_in_window(db, payload.round_id, action='运行选拔')
    result = service.run_selection(
        db,
        round_id=payload.round_id,
        confirm_minutes=payload.confirm_minutes,
        dry_run=payload.dry_run,
        actor=actor,
        ip=client_ip(request),
    )
    return ok(result, '选拔完成' if not payload.dry_run else '预演完成')


@router.get('/offers')
def list_offers(
    round_id: int | None = None,
    status: models.OfferStatus | None = None,
    mentor_id: int | None = None,
    keyword: str = '',
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    query = db.query(models.Offer)
    if round_id:
        query = query.filter(models.Offer.round_id == round_id)
    if status:
        query = query.filter(models.Offer.status == status)
    if mentor_id:
        query = query.filter(models.Offer.mentor_id == mentor_id)
    if keyword:
        like = f'%{keyword}%'
        query = query.join(models.User, models.User.id == models.Offer.student_id).filter(
            or_(models.User.name.like(like), models.User.student_no.like(like))
        )
    total = query.count()
    rows = query.order_by(models.Offer.id.desc()).limit(limit).offset(offset).all()

    items = []
    for row in rows:
        student = db.get(models.User, row.student_id)
        mentor = db.get(models.Mentor, row.mentor_id)
        lab = db.get(models.Lab, mentor.lab_id) if mentor else None
        items.append(
            {
                'id': row.id,
                'student_id': row.student_id,
                'student_no': student.student_no if student else '',
                'student_name': student.name if student else '',
                'mentor_id': row.mentor_id,
                'mentor_name': mentor.name if mentor else '',
                'lab_name': lab.name if lab else '',
                'round_id': row.round_id,
                'offer_type': row.offer_type,
                'status': row.status,
                'reason': row.reason,
                'created_at': row.created_at,
                'expires_at': row.expires_at,
                'confirmed_at': row.confirmed_at,
            }
        )
    return ok({'total': total, 'limit': limit, 'offset': offset, 'items': items})


@router.post('/expire-offers')
def expire_offers(
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    count = service.expire_offers(
        db, now=utcnow(), actor=actor, ip=client_ip(request)
    )
    return ok({'expired': count})


@router.post('/fill-vacancy/{mentor_id}')
def fill_vacancy(
    mentor_id: int,
    request: Request,
    payload: FillVacancyIn | None = None,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    body = payload or FillVacancyIn()
    result = service.fill_vacancy(
        db,
        mentor_id=mentor_id,
        round_id=body.round_id,
        confirm_minutes=body.confirm_minutes,
        actor=actor,
        ip=client_ip(request),
    )
    return ok(result)


@router.post('/adjust')
def adjust(
    payload: AdjustIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    ensure_in_window(db, payload.round_id, action='统筹调剂')
    result = service.adjust(
        db,
        round_id=payload.round_id,
        dry_run=payload.dry_run,
        confirm_minutes=payload.confirm_minutes,
        actor=actor,
        ip=client_ip(request),
    )
    return ok(result)


@router.post('/assign-talk')
def assign_talk(
    payload: AssignTalkIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    offer = service.assign_talk(
        db,
        student_id=payload.student_id,
        mentor_id=payload.mentor_id,
        round_id=payload.round_id,
        reason=payload.reason,
        actor=actor,
        ip=client_ip(request),
    )
    return ok(
        {'offer_id': offer.id, 'student_id': offer.student_id, 'mentor_id': offer.mentor_id}
    )


@router.get('/audit-logs')
def audit_logs(
    action: str = '',
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    query = db.query(models.AuditLog)
    if action:
        query = query.filter(models.AuditLog.action == action)
    total = query.count()
    rows = query.order_by(models.AuditLog.id.desc()).limit(limit).offset(offset).all()
    return ok(
        {
            'total': total,
            'limit': limit,
            'offset': offset,
            'items': [
                {
                    'id': r.id,
                    'actor': r.actor,
                    'action': r.action,
                    'entity': r.entity,
                    'entity_id': r.entity_id,
                    'before_json': r.before_json,
                    'after_json': r.after_json,
                    'ip': r.ip,
                    'created_at': r.created_at,
                }
                for r in rows
            ],
        }
    )


@router.get('/dashboard')
def dashboard(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    now = utcnow()
    quota_total = db.query(func.coalesce(func.sum(models.Mentor.quota), 0)).scalar() or 0
    confirmed = (
        db.query(models.Offer)
        .filter(models.Offer.status == models.OfferStatus.confirmed)
        .count()
    )
    pending = (
        db.query(models.Offer)
        .filter(models.Offer.status == models.OfferStatus.pending)
        .count()
    )
    return ok(
        {
            'labs': db.query(models.Lab).count(),
            'mentors': db.query(models.Mentor).count(),
            'quota_total': int(quota_total),
            'students': db.query(models.User)
            .filter(models.User.role == models.Role.student)
            .count(),
            'intentions': db.query(models.Intention).count(),
            'interviews': db.query(models.Interview).count(),
            'offers_pending': pending,
            'offers_confirmed': confirmed,
            'enrolled': confirmed,
            'rounds_open': [
                r.name
                for r in db.query(models.Round)
                .filter(models.Round.starts_at <= now, models.Round.ends_at >= now)
                .all()
            ],
            'quota_left': int(quota_total) - confirmed - pending,
        }
    )


@router.get('/students')
def list_students(
    keyword: str = '',
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    query = db.query(models.User).filter(models.User.role == models.Role.student)
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(models.User.name.like(like), models.User.student_no.like(like)))
    total = query.count()
    rows = query.order_by(models.User.id).limit(limit).offset(offset).all()
    return ok(
        {
            'total': total,
            'items': [
                {
                    'id': s.id,
                    'student_no': s.student_no,
                    'name': s.name,
                    'obey_internal': s.obey_internal,
                    'obey_cross': s.obey_cross,
                    'is_active': s.is_active,
                }
                for s in rows
            ],
        }
    )

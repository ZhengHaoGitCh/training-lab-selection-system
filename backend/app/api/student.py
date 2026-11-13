from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models
from ..core.database import get_db
from ..core.clock import utcnow
from ..core.deps import (
    client_ip,
    ensure_in_window,
    get_current_student,
    write_audit,
)
from ..core.errors import AppError, ErrorCode
from ..core.response import ok
from ..schemas import ConfirmIn, IntentionIn
from ..services import selection_service as service

router = APIRouter(prefix='/student', tags=['student'])


def intention_views(db: Session, student_id: int, round_id: int | None = None) -> list[dict]:
    query = db.query(models.Intention).filter(models.Intention.student_id == student_id)
    if round_id:
        query = query.filter(models.Intention.round_id == round_id)
    out = []
    for row in query.order_by(models.Intention.priority).all():
        mentor = db.get(models.Mentor, row.mentor_id)
        lab = db.get(models.Lab, mentor.lab_id) if mentor else None
        out.append(
            {
                'id': row.id,
                'student_id': row.student_id,
                'mentor_id': row.mentor_id,
                'mentor_name': mentor.name if mentor else '',
                'lab_id': mentor.lab_id if mentor else 0,
                'lab_name': lab.name if lab else '',
                'round_id': row.round_id,
                'priority': row.priority,
                'created_at': row.created_at,
            }
        )
    return out


@router.get('/intentions')
def list_intentions(
    round_id: int | None = None,
    user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return ok(intention_views(db, user.id, round_id))


@router.post('/intentions')
def submit_intentions(
    payload: IntentionIn,
    request: Request,
    user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    ensure_in_window(db, payload.round_id, action='志愿填报')

    mentors = (
        db.query(models.Mentor)
        .filter(
            models.Mentor.id.in_(payload.mentor_ids),
            models.Mentor.is_active.is_(True),
        )
        .all()
    )
    if len(mentors) != len(payload.mentor_ids):
        raise AppError(ErrorCode.PARAM, '存在无效或已停用的导师志愿')

    if payload.mentor_ids:
        lab_ids = {m.lab_id for m in mentors}
        total_capacity = 0
        for lab_id in lab_ids:
            lab = db.get(models.Lab, lab_id)
            total_capacity += lab.capacity if lab else 0
        if total_capacity == 0:
            raise AppError(ErrorCode.CONFLICT, '所选实训室尚未开放名额')

    db.query(models.Intention).filter(
        models.Intention.student_id == user.id,
        models.Intention.round_id == payload.round_id,
    ).delete(synchronize_session=False)

    for priority, mentor_id in enumerate(payload.mentor_ids, start=1):
        db.add(
            models.Intention(
                student_id=user.id,
                mentor_id=mentor_id,
                round_id=payload.round_id,
                priority=priority,
            )
        )

    user.obey_internal = payload.obey_internal
    user.obey_cross = payload.obey_cross
    db.commit()

    write_audit(
        db,
        actor=user,
        action='submit_intentions',
        entity='round',
        entity_id=payload.round_id,
        after={
            'mentor_ids': payload.mentor_ids,
            'obey_internal': payload.obey_internal,
            'obey_cross': payload.obey_cross,
        },
        ip=client_ip(request),
        commit=True,
    )
    return ok(intention_views(db, user.id, payload.round_id), '志愿已保存')


@router.delete('/intentions/{intention_id}')
def delete_intention(
    intention_id: int,
    user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    row = db.get(models.Intention, intention_id)
    if not row or row.student_id != user.id:
        raise AppError(ErrorCode.NOT_FOUND, '志愿不存在')
    ensure_in_window(db, row.round_id, action='志愿修改')
    db.delete(row)
    db.commit()
    return ok({'deleted': intention_id})


@router.get('/offers')
def my_offers(
    user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return ok(service.student_offer_views(db, user.id))


@router.post('/offers/confirm-unique')
def confirm_unique_offer(
    payload: ConfirmIn,
    request: Request,
    user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    offer = service.confirm_offer(
        db,
        student=user,
        mentor_id=payload.mentor_id,
        now=utcnow(),
        actor=user,
        ip=client_ip(request),
    )
    return ok(
        {
            'confirmed_offer_id': offer.id,
            'mentor_id': offer.mentor_id,
            'status': offer.status.value,
            'confirmed_at': offer.confirmed_at,
        },
        '确认成功',
    )


@router.get('/status')
def my_status(
    user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    confirmed = (
        db.query(models.Offer)
        .filter(
            models.Offer.student_id == user.id,
            models.Offer.status == models.OfferStatus.confirmed,
        )
        .first()
    )
    pending = (
        db.query(models.Offer)
        .filter(
            models.Offer.student_id == user.id,
            models.Offer.status == models.OfferStatus.pending,
        )
        .count()
    )
    intentions = (
        db.query(models.Intention).filter(models.Intention.student_id == user.id).count()
    )
    interviews = (
        db.query(models.Interview).filter(models.Interview.student_id == user.id).count()
    )

    if confirmed:
        stage = 'enrolled'
    elif pending:
        stage = 'offered'
    elif interviews:
        stage = 'interviewed'
    elif intentions:
        stage = 'applied'
    else:
        stage = 'not_applied'

    mentor = db.get(models.Mentor, confirmed.mentor_id) if confirmed else None
    lab = db.get(models.Lab, mentor.lab_id) if mentor else None
    return ok(
        {
            'stage': stage,
            'intentions': intentions,
            'interviews': interviews,
            'pending_offers': pending,
            'obey_internal': user.obey_internal,
            'obey_cross': user.obey_cross,
            'final_mentor': mentor.name if mentor else None,
            'final_lab': lab.name if lab else None,
            'updated_at': utcnow(),
        }
    )


@router.get('/schedule')
def schedule(
    user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
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

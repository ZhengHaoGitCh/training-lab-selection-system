from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models
from ..core.database import get_db
from ..core.clock import utcnow
from ..core.deps import client_ip, get_current_student, require_admin, write_audit
from ..core.errors import AppError, ErrorCode
from ..core.response import ok
from ..schemas import AppealHandleIn, AppealIn, PublicationIn

router = APIRouter(tags=['publication'])


@router.get('/meta/labs')
def public_labs(db: Session = Depends(get_db)):
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
                'mentors': [
                    {
                        'id': m.id,
                        'name': m.name,
                        'quota': m.quota,
                        'quota_left': max(
                            0,
                            m.quota
                            - sum(
                                1
                                for o in db.query(models.Offer)
                                .filter(models.Offer.mentor_id == m.id)
                                .all()
                                if o.status in (models.OfferStatus.pending, models.OfferStatus.confirmed)
                            ),
                        ),
                        'requirement': m.requirement,
                    }
                    for m in mentors
                ],
            }
        )
    return ok(items)


@router.get('/meta/mentors')
def public_mentors(lab_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Mentor).filter(models.Mentor.is_active.is_(True))
    if lab_id:
        query = query.filter(models.Mentor.lab_id == lab_id)
    return ok(
        [
            {
                'id': m.id,
                'lab_id': m.lab_id,
                'lab_name': m.lab.name if m.lab else '',
                'name': m.name,
                'quota': m.quota,
                'requirement': m.requirement,
            }
            for m in query.order_by(models.Mentor.id).all()
        ]
    )


@router.get('/meta/rounds')
def public_rounds(db: Session = Depends(get_db)):
    now = utcnow()
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
            for r in db.query(models.Round).order_by(models.Round.starts_at).all()
        ]
    )


@router.post('/admin/publications')
def create_publication(
    payload: PublicationIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    row = models.Publication(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(
        db, actor=actor, action='create_publication', entity='publication', entity_id=row.id,
        after=payload.model_dump(mode='json'), ip=client_ip(request), commit=True,
    )
    return ok({'id': row.id, 'status': row.status.value})


@router.post('/admin/publications/{publication_id}/publish')
def publish(
    publication_id: int,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    row = db.get(models.Publication, publication_id)
    if not row:
        raise AppError(ErrorCode.NOT_FOUND, '公示不存在')
    row.status = models.PublicationStatus.published
    row.published_at = utcnow()
    row.published_by = actor.id
    db.commit()
    write_audit(
        db, actor=actor, action='publish', entity='publication', entity_id=row.id, commit=True,
    )
    return ok({'id': row.id, 'status': row.status.value, 'published_at': row.published_at})


@router.get('/admin/publications')
def list_publications(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    rows = db.query(models.Publication).order_by(models.Publication.id.desc()).all()
    return ok(
        [
            {
                'id': r.id,
                'round_id': r.round_id,
                'title': r.title,
                'content': r.content,
                'status': r.status,
                'published_at': r.published_at,
                'created_at': r.created_at,
            }
            for r in rows
        ]
    )


@router.get('/publications')
def public_list(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Publication)
        .filter(models.Publication.status == models.PublicationStatus.published)
        .order_by(models.Publication.published_at.desc())
        .all()
    )
    return ok(
        [
            {
                'id': r.id,
                'round_id': r.round_id,
                'title': r.title,
                'content': r.content,
                'published_at': r.published_at,
            }
            for r in rows
        ]
    )


@router.post('/student/appeals')
def create_appeal(
    payload: AppealIn,
    request: Request,
    student: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    open_round = (
        db.query(models.Round)
        .filter(
            models.Round.starts_at <= utcnow(),
            models.Round.ends_at >= utcnow(),
        )
        .order_by(models.Round.id.desc())
        .first()
    )
    row = models.Appeal(
        student_id=student.id,
        publication_id=payload.publication_id,
        content=payload.content,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(
        db, actor=student, action='create_appeal', entity='appeal', entity_id=row.id,
        after={'content': payload.content[:200]}, ip=client_ip(request), commit=True,
    )
    return ok({'id': row.id, 'status': row.status.value, 'round': open_round.name if open_round else None})


@router.get('/student/appeals')
def my_appeals(
    student: models.User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.Appeal)
        .filter(models.Appeal.student_id == student.id)
        .order_by(models.Appeal.id.desc())
        .all()
    )
    return ok(
        [
            {
                'id': r.id,
                'publication_id': r.publication_id,
                'content': r.content,
                'status': r.status,
                'reply': r.reply,
                'created_at': r.created_at,
                'handled_at': r.handled_at,
            }
            for r in rows
        ]
    )


@router.get('/admin/appeals')
def list_appeals(
    status: models.AppealStatus | None = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    query = db.query(models.Appeal)
    if status:
        query = query.filter(models.Appeal.status == status)
    items = []
    for row in query.order_by(models.Appeal.id.desc()).all():
        student = db.get(models.User, row.student_id)
        items.append(
            {
                'id': row.id,
                'student_id': row.student_id,
                'student_name': student.name if student else '',
                'publication_id': row.publication_id,
                'content': row.content,
                'status': row.status,
                'reply': row.reply,
                'created_at': row.created_at,
                'handled_at': row.handled_at,
            }
        )
    return ok(items)


@router.post('/admin/appeals/{appeal_id}/handle')
def handle_appeal(
    appeal_id: int,
    payload: AppealHandleIn,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    row = db.get(models.Appeal, appeal_id)
    if not row:
        raise AppError(ErrorCode.NOT_FOUND, '申诉不存在')
    row.status = payload.status
    row.reply = payload.reply
    row.handled_by = actor.id
    row.handled_at = utcnow()
    db.commit()
    write_audit(
        db, actor=actor, action='handle_appeal', entity='appeal', entity_id=row.id,
        after={'status': payload.status.value, 'reply': payload.reply[:200]}, commit=True,
    )
    return ok({'id': row.id, 'status': row.status.value})


@router.get('/admin/enrollment')
def enrollment_list(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    rows = (
        db.query(models.Offer)
        .filter(models.Offer.status == models.OfferStatus.confirmed)
        .order_by(models.Offer.mentor_id, models.Offer.confirmed_at)
        .all()
    )
    items = []
    for row in rows:
        student = db.get(models.User, row.student_id)
        mentor = db.get(models.Mentor, row.mentor_id)
        lab = db.get(models.Lab, mentor.lab_id) if mentor else None
        items.append(
            {
                'student_no': student.student_no if student else '',
                'student_name': student.name if student else '',
                'mentor_name': mentor.name if mentor else '',
                'lab_name': lab.name if lab else '',
                'confirmed_at': row.confirmed_at,
            }
        )
    return ok(items)

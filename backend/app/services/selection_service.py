"""数据库编排层：把纯领域函数与 SQLAlchemy 实体串起来。

所有写操作均写审计日志，保证“名单生成、改分、确认、递补、调剂”可追溯。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..core.errors import AppError, ErrorCode
from ..core.clock import utcnow
from ..core.config import settings
from . import selection as sel


def _to_domain_interview(row: models.Interview) -> sel.Interview:
    return sel.Interview(
        student_id=row.student_id,
        mentor_id=row.mentor_id,
        score_attitude=row.score_attitude,
        score_logic=row.score_logic,
        score_code=row.score_code,
        score_time=row.score_time,
    )


def _to_domain_offer(row: models.Offer) -> sel.Offer:
    return sel.Offer(
        id=row.id,
        student_id=row.student_id,
        mentor_id=row.mentor_id,
        round_id=row.round_id,
        status=sel.OfferStatus(row.status.value),
        expires_at=row.expires_at,
        confirmed_at=row.confirmed_at,
        offer_type=row.offer_type.value,
        reason=row.reason,
    )


def sync_offer_from_domain(row: models.Offer, offer: sel.Offer) -> None:
    row.status = models.OfferStatus(offer.status.value)
    row.confirmed_at = offer.confirmed_at


def mentor_capacity(mentor: models.Mentor) -> int:
    lab = mentor.lab
    if lab and lab.capacity:
        return min(mentor.quota, lab.capacity)
    return mentor.quota


def remaining_quota(db: Session, mentor: models.Mentor) -> int:
    rows = db.query(models.Offer).filter(models.Offer.mentor_id == mentor.id).all()
    offers = [_to_domain_offer(r) for r in rows]
    return sel.available_quota(offers, mentor.id, mentor.quota, mentor_capacity(mentor))


def run_selection(db: Session, *, round_id: int, confirm_minutes: int, dry_run: bool,
                  actor: models.User | None, ip: str = '') -> dict:
    """执行一轮选拔：按导师分别排序，生成拟录取/递补/内部候选并落库。"""
    round_obj = db.get(models.Round, round_id)
    if not round_obj:
        raise AppError(ErrorCode.NOT_FOUND, f'轮次 {round_id} 不存在')

    interviews = (
        db.query(models.Interview)
        .filter(models.Interview.round_id == round_id)
        .all()
    )
    if not interviews:
        raise AppError(ErrorCode.PARAM, '该轮次尚未录入面试评分')

    counts = {d: 0 for d in models.Decision}
    created = skipped = 0
    expires_at = utcnow() + timedelta(minutes=confirm_minutes)

    for mentor in db.query(models.Mentor).filter(models.Mentor.is_active.is_(True)).all():
        mentor_rows = [x for x in interviews if x.mentor_id == mentor.id]
        if not mentor_rows:
            continue

        domain_rows = [_to_domain_interview(x) for x in mentor_rows]
        quota = mentor_capacity(mentor)
        decisions = sel.rank_interviews(
            domain_rows,
            quota,
            waitlist_size=settings.waitlist_min_size,
            internal_ratio=settings.internal_candidate_ratio,
        )

        for row in mentor_rows:
            decision = decisions[row.student_id]
            counts[models.Decision(decision.value)] += 1
            if dry_run:
                continue
            row.decision = models.Decision(decision.value)

            if decision is not sel.Decision.PROPOSED:
                continue

            existing = (
                db.query(models.Offer)
                .filter(
                    models.Offer.student_id == row.student_id,
                    models.Offer.mentor_id == mentor.id,
                    models.Offer.round_id == round_id,
                )
                .first()
            )
            if existing:
                skipped += 1
                continue
            if remaining_quota(db, mentor) <= 0:
                skipped += 1
                continue

            db.add(
                models.Offer(
                    student_id=row.student_id,
                    mentor_id=mentor.id,
                    round_id=round_id,
                    offer_type=models.OfferType.regular,
                    status=models.OfferStatus.pending,
                    expires_at=expires_at,
                    reason=f'{round_obj.name} 拟录取',
                )
            )
            db.flush()
            created += 1

    if not dry_run:
        db.commit()
        from ..core.deps import write_audit

        write_audit(
            db,
            actor=actor,
            action='run_selection',
            entity='round',
            entity_id=round_id,
            after={k.value: v for k, v in counts.items()} | {'offers_created': created},
            ip=ip,
            commit=True,
        )

    return {
        'round_id': round_id,
        'proposed': counts[models.Decision.proposed],
        'waitlist': counts[models.Decision.waitlist],
        'internal_candidate': counts[models.Decision.internal_candidate],
        'rejected': counts[models.Decision.rejected],
        'offers_created': created,
        'offers_skipped': skipped,
        'dry_run': dry_run,
    }


def student_offer_views(db: Session, student_id: int) -> list[dict]:
    rows = (
        db.query(models.Offer)
        .filter(models.Offer.student_id == student_id)
        .order_by(models.Offer.created_at.desc())
        .all()
    )
    out = []
    for row in rows:
        mentor = db.get(models.Mentor, row.mentor_id)
        lab = db.get(models.Lab, mentor.lab_id) if mentor else None
        out.append(
            {
                'id': row.id,
                'student_id': row.student_id,
                'mentor_id': row.mentor_id,
                'round_id': row.round_id,
                'offer_type': row.offer_type,
                'status': row.status,
                'reason': row.reason,
                'created_at': row.created_at,
                'expires_at': row.expires_at,
                'confirmed_at': row.confirmed_at,
                'mentor_name': mentor.name if mentor else '',
                'lab_name': lab.name if lab else '',
            }
        )
    return out


def confirm_offer(db: Session, *, student: models.User, mentor_id: int | None,
                  now: datetime | None, actor: models.User | None, ip: str = '') -> models.Offer:
    rows = (
        db.query(models.Offer)
        .filter(models.Offer.student_id == student.id)
        .all()
    )
    offers = [_to_domain_offer(r) for r in rows]
    try:
        chosen = sel.confirm_unique_offer(offers, student.id, mentor_id, now)
    except sel.DomainError as exc:
        db.rollback()
        raise AppError(exc.code, exc.message) from None

    by_id = {o.id: o for o in offers}
    for row in rows:
        domain = by_id.get(row.id)
        if domain:
            sync_offer_from_domain(row, domain)

    claimed = db.get(models.Offer, chosen.id)
    if claimed and claimed.reason == '':
        claimed.reason = '学生确认'
    db.commit()
    db.refresh(claimed)

    from ..core.deps import write_audit

    write_audit(
        db,
        actor=actor or student,
        action='confirm_offer',
        entity='offer',
        entity_id=claimed.id,
        after={'mentor_id': claimed.mentor_id, 'status': claimed.status.value},
        ip=ip,
        commit=True,
    )
    return claimed


def expire_offers(db: Session, *, now: datetime | None, actor: models.User | None,
                  ip: str = '') -> int:
    rows = (
        db.query(models.Offer)
        .filter(models.Offer.status == models.OfferStatus.pending)
        .all()
    )
    offers = [_to_domain_offer(r) for r in rows]
    expired = sel.expire_pending_offers(offers, now)
    if not expired:
        return 0
    by_id = {o.id: o for o in offers}
    for row in rows:
        domain = by_id.get(row.id)
        if domain:
            sync_offer_from_domain(row, domain)
    db.commit()
    from ..core.deps import write_audit

    write_audit(
        db,
        actor=actor,
        action='expire_offers',
        entity='offer',
        entity_id=0,
        after={'expired_ids': [o.id for o in expired]},
        ip=ip,
        commit=True,
    )
    return len(expired)


def fill_vacancy(db: Session, *, mentor_id: int, round_id: int | None,
                 confirm_minutes: int, actor: models.User | None, ip: str = '') -> dict:
    mentor = db.get(models.Mentor, mentor_id)
    if not mentor:
        raise AppError(ErrorCode.NOT_FOUND, f'导师 {mentor_id} 不存在')

    all_offers = db.query(models.Offer).filter(models.Offer.mentor_id == mentor_id).all()
    domain_offers = [_to_domain_offer(o) for o in all_offers]

    round_obj_id = round_id
    if round_obj_id is None:
        latest = (
            db.query(models.Offer.round_id)
            .filter(models.Offer.mentor_id == mentor_id)
            .order_by(models.Offer.round_id.desc())
            .first()
        )
        round_obj_id = latest[0] if latest else db.query(func.max(models.Round.id)).scalar() or 1

    interviews = (
        db.query(models.Interview)
        .filter(models.Interview.mentor_id == mentor_id)
        .all()
    )
    domain_rows = [_to_domain_interview(x) for x in interviews]
    quota = mentor_capacity(mentor)

    candidate = sel.next_waitlist_candidate(
        domain_rows, domain_offers, mentor_id, mentor.quota, quota
    )
    if not candidate:
        return {'filled': False, 'reason': '无可递补候选或名额已满'}

    duplicate = (
        db.query(models.Offer)
        .filter(
            models.Offer.student_id == candidate.student_id,
            models.Offer.mentor_id == mentor_id,
            models.Offer.status.in_([models.OfferStatus.pending, models.OfferStatus.confirmed]),
        )
        .first()
    )
    if duplicate:
        return {'filled': False, 'reason': '该学生已有待确认或已确认意向'}

    offer = models.Offer(
        student_id=candidate.student_id,
        mentor_id=mentor_id,
        round_id=round_obj_id,
        offer_type=models.OfferType.supplement,
        status=models.OfferStatus.pending,
        expires_at=utcnow() + timedelta(minutes=confirm_minutes),
        reason='递补录取',
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    from ..core.deps import write_audit

    write_audit(
        db,
        actor=actor,
        action='fill_vacancy',
        entity='offer',
        entity_id=offer.id,
        after={'student_id': candidate.student_id, 'mentor_id': mentor_id},
        ip=ip,
        commit=True,
    )
    return {
        'filled': True,
        'offer_id': offer.id,
        'student_id': candidate.student_id,
        'round_id': offer.round_id,
    }


def _vacancies(db: Session) -> list[dict]:
    """所有仍有余额的在职导师，形如 ``{'mentor_id','lab_id','quota_left'}``。

    调剂分两轮使用同一份名单：先在**同实训室**范围内按内部服从匹配，
    再在**全院任意实训室**范围内按跨室服从匹配。
    """
    vacancies: list[dict] = []
    for mentor in db.query(models.Mentor).filter(models.Mentor.is_active.is_(True)).all():
        left = remaining_quota(db, mentor)
        if left <= 0:
            continue
        vacancies.append(
            {'mentor_id': mentor.id, 'lab_id': mentor.lab_id, 'quota_left': left}
        )
    return vacancies


def _unplaced_students(db: Session, round_id: int) -> list[sel.Candidate]:
    engaged = {
        row[0]
        for row in db.query(models.Offer.student_id)
        .filter(models.Offer.status.in_([models.OfferStatus.confirmed, models.OfferStatus.pending]))
        .all()
    }
    best: dict[int, models.Interview] = {}
    for row in db.query(models.Interview).filter(models.Interview.round_id == round_id).all():
        current = best.get(row.student_id)
        if current is None or _to_domain_interview(row).total > _to_domain_interview(current).total:
            best[row.student_id] = row

    out: list[sel.Candidate] = []
    for student_id, row in best.items():
        if student_id in engaged:
            continue
        student = db.get(models.User, student_id)
        if not student:
            continue
        interview = _to_domain_interview(row)
        # 用面试导师所属实训室作为“原实训室”
        mentor = db.get(models.Mentor, row.mentor_id)
        out.append(
            sel.Candidate(
                student_id=student_id,
                lab_id=mentor.lab_id if mentor else 0,
                score=interview.total,
                obey_internal=student.obey_internal,
                obey_cross=student.obey_cross,
            )
        )
    return out


def adjust(db: Session, *, round_id: int, dry_run: bool, confirm_minutes: int,
           actor: models.User | None, ip: str = '') -> dict:
    if not db.get(models.Round, round_id):
        raise AppError(ErrorCode.NOT_FOUND, f'轮次 {round_id} 不存在')

    # 同一份余额名单供两轮使用；plan_adjustments 会按导师同步扣减，避免超发
    vacancies = _vacancies(db)
    candidates = _unplaced_students(db, round_id)
    if not candidates:
        return {'allocations': [], 'talk_list': [], 'offers_created': 0}

    allocations, talk = sel.plan_adjustments(candidates, vacancies, vacancies)

    created = 0
    if not dry_run:
        for item in allocations:
            offer_type = (
                models.OfferType.internal
                if item['mode'] == 'internal'
                else models.OfferType.cross
            )
            db.add(
                models.Offer(
                    student_id=item['student_id'],
                    mentor_id=item['mentor_id'],
                    round_id=round_id,
                    offer_type=offer_type,
                    status=models.OfferStatus.pending,
                    expires_at=utcnow() + timedelta(minutes=confirm_minutes),
                    reason=f"{'实训室内部' if item['mode'] == 'internal' else '全院跨实训室'}调剂",
                )
            )
            created += 1
        db.commit()

        from ..core.deps import write_audit

        write_audit(
            db,
            actor=actor,
            action='adjust',
            entity='round',
            entity_id=round_id,
            after={'allocations': allocations, 'talk': [t['student_id'] for t in talk]},
            ip=ip,
            commit=True,
        )

    return {'allocations': allocations, 'talk_list': talk, 'offers_created': created}


def assign_talk(db: Session, *, student_id: int, mentor_id: int, round_id: int,
                reason: str, actor: models.User | None, ip: str = '') -> models.Offer:
    student = db.get(models.User, student_id)
    mentor = db.get(models.Mentor, mentor_id)
    if not student or student.role != models.Role.student:
        raise AppError(ErrorCode.NOT_FOUND, '学生不存在')
    if not mentor:
        raise AppError(ErrorCode.NOT_FOUND, '导师不存在')
    if remaining_quota(db, mentor) <= 0:
        raise AppError(ErrorCode.CONFLICT, '该导师名额已满')

    offer = models.Offer(
        student_id=student_id,
        mentor_id=mentor_id,
        round_id=round_id,
        offer_type=models.OfferType.assigned,
        status=models.OfferStatus.pending,
        reason=reason,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    from ..core.deps import write_audit

    write_audit(
        db,
        actor=actor,
        action='assign_talk',
        entity='offer',
        entity_id=offer.id,
        after={'student_id': student_id, 'mentor_id': mentor_id, 'reason': reason},
        ip=ip,
        commit=True,
    )
    return offer

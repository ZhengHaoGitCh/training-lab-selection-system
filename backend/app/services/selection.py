"""选组选拔核心领域逻辑（纯函数，无数据库依赖，便于单元测试）。

设计要点：
- 分数四维加总，满分 100（25/20/35/20）。
- 同分按学号升序打破平局，保证结果可复现、可审计。
- 拟录取（proposed）不超导师剩余名额；内部调剂候选与递补均不占用名额。
- 确认阶段：单意向自动确认，多意向必须显式选择唯一去向；逾期释放。
- 补录：按分数递补一位，且不超过实训室容量。
- 调剂：内部调剂 → 全院跨实训室调剂 → 约谈安置。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Sequence


def utc_now() -> datetime:
    """统一使用 naive UTC，便于与数据库 DATETIME 字段直接比较。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Decision(str, Enum):
    PROPOSED = 'proposed'
    WAITLIST = 'waitlist'
    INTERNAL_CANDIDATE = 'internal_candidate'
    REJECTED = 'rejected'


class OfferStatus(str, Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    EXPIRED = 'expired'


class DomainError(Exception):
    """领域规则冲突。code 与 API 错误码对齐。"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


SCORE_LIMITS = {
    'score_attitude': 25,
    'score_logic': 20,
    'score_code': 35,
    'score_time': 20,
}
FULL_SCORE = sum(SCORE_LIMITS.values())


@dataclass(frozen=True)
class Interview:
    student_id: int
    mentor_id: int
    score_attitude: int = 0
    score_logic: int = 0
    score_code: int = 0
    score_time: int = 0

    @property
    def total(self) -> int:
        return total_score(self)

    def sort_key(self) -> tuple[int, int]:
        return (-self.total, self.student_id)


@dataclass
class Offer:
    id: int
    student_id: int
    mentor_id: int
    round_id: int
    status: OfferStatus = OfferStatus.PENDING
    expires_at: datetime | None = None
    confirmed_at: datetime | None = None
    offer_type: str = 'regular'
    reason: str = ''


@dataclass
class Candidate:
    student_id: int
    lab_id: int
    score: int = 0
    obey_internal: bool = False
    obey_cross: bool = False
    assigned: bool = False
    extra: dict = field(default_factory=dict)

    def sort_key(self) -> tuple[int, int]:
        return (-self.score, self.student_id)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def total_score(interview: Interview) -> int:
    return (
        clamp(interview.score_attitude, 0, SCORE_LIMITS['score_attitude'])
        + clamp(interview.score_logic, 0, SCORE_LIMITS['score_logic'])
        + clamp(interview.score_code, 0, SCORE_LIMITS['score_code'])
        + clamp(interview.score_time, 0, SCORE_LIMITS['score_time'])
    )


def rank_interviews(
    interviews: Iterable[Interview],
    quota: int,
    *,
    waitlist_size: int = 3,
    internal_ratio: float = 0.2,
) -> dict[int, Decision]:
    """单个导师维度内的排序与结论。

    名额顺序：proposed → internal_candidate（保底候选，可参与内部调剂）
    → waitlist → rejected。内部候选不占用拟录取名额。
    """
    quota = max(0, quota)
    # 至少保留 1 个内部调剂候选作为保底，名额越多候补越多
    internal_slots = max(1, int(quota * internal_ratio)) if quota else 0
    waitlist_slots = max(waitlist_size, quota)

    items = sorted(interviews, key=Interview.sort_key)
    out: dict[int, Decision] = {}
    proposed = internal = waitlist = 0

    for item in items:
        if proposed < quota:
            out[item.student_id] = Decision.PROPOSED
            proposed += 1
        elif internal < internal_slots:
            out[item.student_id] = Decision.INTERNAL_CANDIDATE
            internal += 1
        elif waitlist < waitlist_slots:
            out[item.student_id] = Decision.WAITLIST
            waitlist += 1
        else:
            out[item.student_id] = Decision.REJECTED
    return out


def active_pending(offers: Iterable[Offer], student_id: int) -> list[Offer]:
    return [
        o
        for o in offers
        if o.student_id == student_id and o.status == OfferStatus.PENDING
    ]


def confirm_unique_offer(
    offers: Sequence[Offer],
    student_id: int,
    mentor_id: int | None = None,
    now: datetime | None = None,
) -> Offer:
    """确认唯一去向。多意向且未指定 mentor_id 时报 4001。"""
    now = now or utc_now()

    already = [
        o
        for o in offers
        if o.student_id == student_id and o.status == OfferStatus.CONFIRMED
    ]
    if already:
        if mentor_id is not None and already[0].mentor_id != mentor_id:
            raise DomainError(4001, '已确认其他实训室，不能重复确认')
        return already[0]

    pending = active_pending(offers, student_id)
    if not pending:
        raise DomainError(4001, '没有可确认的拟录取意向')

    if mentor_id is None:
        if len(pending) != 1:
            raise DomainError(4001, '收到多个拟录取意向，必须显式选择唯一去向')
        chosen = pending[0]
    else:
        chosen = next((o for o in pending if o.mentor_id == mentor_id), None)
        if chosen is None:
            raise DomainError(4001, '所选导师不在可确认意向中')

    if chosen.expires_at and now > chosen.expires_at:
        chosen.status = OfferStatus.EXPIRED
        raise DomainError(3001, '确认窗口已截止')

    chosen.status = OfferStatus.CONFIRMED
    chosen.confirmed_at = now
    for other in pending:
        if other is not chosen:
            other.status = OfferStatus.REJECTED
    return chosen


def expire_pending_offers(
    offers: Iterable[Offer], now: datetime | None = None
) -> list[Offer]:
    now = now or utc_now()
    expired: list[Offer] = []
    for offer in offers:
        if (
            offer.status == OfferStatus.PENDING
            and offer.expires_at is not None
            and now > offer.expires_at
        ):
            offer.status = OfferStatus.EXPIRED
            expired.append(offer)
    return expired


def confirmed_count(offers: Iterable[Offer], mentor_id: int) -> int:
    return sum(
        1
        for o in offers
        if o.mentor_id == mentor_id and o.status == OfferStatus.CONFIRMED
    )


def reserved_count(offers: Iterable[Offer], mentor_id: int) -> int:
    """已确认 + 待确认共同占用的名额。"""
    return sum(
        1
        for o in offers
        if o.mentor_id == mentor_id
        and o.status in (OfferStatus.CONFIRMED, OfferStatus.PENDING)
    )


def available_quota(
    offers: Iterable[Offer], mentor_id: int, quota: int, capacity: int
) -> int:
    limit = min(max(quota, 0), max(capacity, 0)) if capacity else max(quota, 0)
    return max(0, limit - reserved_count(offers, mentor_id))


def next_waitlist_candidate(
    interviews: Iterable[Interview],
    offers: Iterable[Offer],
    mentor_id: int,
    quota: int,
    capacity: int,
) -> Interview | None:
    """按顺位补录一名，跳过已确认/已发出待确认的学生。"""
    if available_quota(offers, mentor_id, quota, capacity) <= 0:
        return None

    taken = {
        o.student_id
        for o in offers
        if o.mentor_id == mentor_id
        and o.status in (OfferStatus.CONFIRMED, OfferStatus.PENDING)
    }
    ranked = sorted(
        (it for it in interviews if it.mentor_id == mentor_id),
        key=Interview.sort_key,
    )
    for item in ranked:
        if item.student_id not in taken:
            return item
    return None


def plan_adjustments(
    candidates: Iterable[Candidate],
    internal_vacancies: Iterable[dict],
    cross_vacancies: Iterable[dict],
) -> tuple[list[dict], list[dict]]:
    """统筹调剂规划。

    internal_vacancies / cross_vacancies 形如
    ``{'mentor_id': 10, 'lab_id': 2, 'quota_left': 1}``（会被就地扣减）。

    同一导师可能同时出现在两个池中（内部池用于同实训室匹配，跨室池用于
    任意实训室匹配）。名额以**导师**为粒度共享：任一次分配都会同步扣减该
    导师在两个池中的剩余名额，避免两轮各自扣减同一份名额造成超发。

    返回 ``(allocations, talk_list)``：
    - allocations: ``{'student_id','mentor_id','lab_id','mode'}``
    - talk_list: 未服从调剂、需约谈安置的学生
    """
    internal = [dict(v) for v in internal_vacancies]
    cross = [dict(v) for v in cross_vacancies]
    quota_pools = internal + cross

    def consume(mentor_id: int) -> None:
        for entry in quota_pools:
            if entry['mentor_id'] == mentor_id:
                entry['quota_left'] = max(0, entry['quota_left'] - 1)

    pool = list(candidates)
    used: set[int] = set()
    allocations: list[dict] = []

    for vacancy in internal:
        while vacancy['quota_left'] > 0:
            eligible = [
                c
                for c in pool
                if c.student_id not in used
                and c.obey_internal
                and c.lab_id == vacancy['lab_id']
            ]
            if not eligible:
                break
            chosen = min(eligible, key=Candidate.sort_key)
            allocations.append(
                {
                    'student_id': chosen.student_id,
                    'mentor_id': vacancy['mentor_id'],
                    'lab_id': vacancy['lab_id'],
                    'mode': 'internal',
                }
            )
            used.add(chosen.student_id)
            consume(vacancy['mentor_id'])

    for vacancy in cross:
        while vacancy['quota_left'] > 0:
            eligible = [
                c for c in pool if c.student_id not in used and c.obey_cross
            ]
            if not eligible:
                break
            chosen = min(eligible, key=Candidate.sort_key)
            allocations.append(
                {
                    'student_id': chosen.student_id,
                    'mentor_id': vacancy['mentor_id'],
                    'lab_id': vacancy['lab_id'],
                    'mode': 'cross',
                }
            )
            used.add(chosen.student_id)
            consume(vacancy['mentor_id'])

    talk = [
        {'student_id': c.student_id, 'lab_id': c.lab_id, 'mode': 'talk'}
        for c in sorted(pool, key=Candidate.sort_key)
        if c.student_id not in used
    ]
    return allocations, talk


def allocate_adjustments(
    students: list[dict],
    internal_vacancies: list[dict],
    cross_vacancies: list[dict],
) -> list[dict]:
    """兼容旧签名的字典版本封装。"""
    candidates = [
        Candidate(
            student_id=s['student_id'],
            lab_id=s.get('lab_id', 0),
            score=s.get('score', 0),
            obey_internal=s.get('obey_internal', False),
            obey_cross=s.get('obey_cross', False),
        )
        for s in students
    ]
    allocations, talk = plan_adjustments(candidates, internal_vacancies, cross_vacancies)
    return allocations + talk

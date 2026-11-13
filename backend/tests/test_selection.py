"""核心选拔算法单元测试（纯函数，无数据库）。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.selection import (
    Candidate,
    Decision,
    DomainError,
    Interview,
    Offer,
    OfferStatus,
    allocate_adjustments,
    available_quota,
    confirm_unique_offer,
    expire_pending_offers,
    next_waitlist_candidate,
    plan_adjustments,
    rank_interviews,
    total_score,
)


def test_total_score_clamps_out_of_range():
    assert total_score(Interview(1, 1, 25, 20, 35, 20)) == 100
    # 越界值被裁剪，不会出现 >100
    assert total_score(Interview(1, 1, 99, 99, 99, 99)) == 100
    assert total_score(Interview(1, 1, -5, 0, 0, 0)) == 0


def test_rank_respects_quota_and_tiebreak_by_student_id():
    interviews = [
        Interview(3, 10, 25, 20, 35, 20),
        Interview(1, 10, 25, 20, 35, 20),
        Interview(2, 10, 10, 10, 10, 10),
    ]
    decisions = rank_interviews(interviews, quota=1)
    # 同分时学号更小者优先
    assert decisions[1] is Decision.PROPOSED
    assert decisions[3] is Decision.INTERNAL_CANDIDATE
    assert decisions[2] is Decision.WAITLIST


def test_rank_zero_quota_all_rejected_or_waitlisted():
    decisions = rank_interviews([Interview(1, 10, 20, 15, 25, 15)], quota=0, waitlist_size=0)
    assert decisions[1] is Decision.REJECTED


def test_single_offer_auto_confirms():
    offers = [Offer(1, 100, 10, 1)]
    chosen = confirm_unique_offer(offers, 100)
    assert chosen.status is OfferStatus.CONFIRMED
    assert chosen.confirmed_at is not None


def test_multiple_offers_require_explicit_choice():
    offers = [Offer(1, 100, 10, 1), Offer(2, 100, 11, 1)]
    with pytest.raises(DomainError) as exc:
        confirm_unique_offer(offers, 100)
    assert exc.value.code == 4001

    chosen = confirm_unique_offer(offers, 100, mentor_id=11)
    assert chosen.mentor_id == 11
    assert {o.status for o in offers} == {OfferStatus.CONFIRMED, OfferStatus.REJECTED}


def test_confirm_with_unknown_mentor_raises():
    offers = [Offer(1, 100, 10, 1)]
    with pytest.raises(DomainError) as exc:
        confirm_unique_offer(offers, 100, mentor_id=99)
    assert exc.value.code == 4001


def test_confirm_is_idempotent():
    offers = [Offer(1, 100, 10, 1)]
    first = confirm_unique_offer(offers, 100)
    second = confirm_unique_offer(offers, 100)
    assert first.id == second.id
    assert sum(1 for o in offers if o.status is OfferStatus.CONFIRMED) == 1


def test_expired_offer_cannot_be_confirmed():
    now = datetime.utcnow()
    offers = [Offer(1, 100, 10, 1, expires_at=now - timedelta(minutes=1))]
    with pytest.raises(DomainError) as exc:
        confirm_unique_offer(offers, 100, now=now)
    assert exc.value.code == 3001
    assert offers[0].status is OfferStatus.EXPIRED


def test_expire_pending_offers_only_touches_overdue():
    now = datetime.utcnow()
    offers = [
        Offer(1, 100, 10, 1, expires_at=now - timedelta(minutes=1)),
        Offer(2, 101, 10, 1, expires_at=now + timedelta(minutes=30)),
        Offer(3, 102, 10, 1),
    ]
    expired = expire_pending_offers(offers, now)
    assert [o.id for o in expired] == [1]
    assert offers[1].status is OfferStatus.PENDING
    assert offers[2].status is OfferStatus.PENDING


def test_next_waitlist_skips_confirmed_and_pending():
    interviews = [
        Interview(100, 10, 25, 20, 35, 20),
        Interview(101, 10, 20, 18, 30, 15),
        Interview(102, 10, 22, 16, 28, 12),
    ]
    offers = [
        Offer(1, 100, 10, 1, status=OfferStatus.CONFIRMED),
        Offer(2, 102, 10, 1, status=OfferStatus.PENDING),
    ]
    candidate = next_waitlist_candidate(interviews, offers, 10, quota=3, capacity=10)
    assert candidate is not None and candidate.student_id == 101


def test_next_waitlist_returns_none_when_full():
    interviews = [Interview(100, 10, 25, 20, 35, 20)]
    offers = [Offer(1, 100, 10, 1, status=OfferStatus.CONFIRMED)]
    assert next_waitlist_candidate(interviews, offers, 10, quota=1, capacity=10) is None


def test_available_quota_never_negative_and_capped_by_capacity():
    offers = [Offer(1, 1, 10, 1, status=OfferStatus.CONFIRMED)]
    assert available_quota(offers, 10, quota=2, capacity=10) == 1
    assert available_quota(offers, 10, quota=5, capacity=1) == 0
    assert available_quota([], 10, quota=0, capacity=5) == 0


def test_adjustment_priority_internal_before_cross():
    students = [
        {'student_id': 1, 'obey_internal': True, 'obey_cross': True, 'lab_id': 2, 'score': 80},
        {'student_id': 2, 'obey_internal': False, 'obey_cross': True, 'lab_id': 3, 'score': 95},
    ]
    internal = [{'mentor_id': 10, 'lab_id': 2, 'quota_left': 1}]
    cross = [{'mentor_id': 20, 'lab_id': 3, 'quota_left': 1}]

    result = allocate_adjustments(students, internal, cross)
    modes = {item['student_id']: item['mode'] for item in result}
    assert modes[1] == 'internal'
    assert modes[2] == 'cross'


def test_adjustment_prefers_higher_score_within_same_mode():
    candidates = [
        Candidate(1, lab_id=2, score=70, obey_internal=True),
        Candidate(2, lab_id=2, score=90, obey_internal=True),
    ]
    allocations, talk = plan_adjustments(
        candidates,
        [{'mentor_id': 10, 'lab_id': 2, 'quota_left': 1}],
        [],
    )
    assert allocations[0]['student_id'] == 2
    assert [t['student_id'] for t in talk] == [1]


def test_adjustment_reports_unwilling_students_as_talk():
    candidates = [Candidate(1, lab_id=2, score=88, obey_internal=False, obey_cross=False)]
    allocations, talk = plan_adjustments(
        candidates,
        [{'mentor_id': 10, 'lab_id': 2, 'quota_left': 2}],
        [{'mentor_id': 20, 'lab_id': 3, 'quota_left': 2}],
    )
    assert allocations == []
    assert talk[0]['student_id'] == 1 and talk[0]['mode'] == 'talk'


def test_cross_adjustment_can_place_student_from_any_lab():
    """跨室调剂阶段不再排除原实训室——内部优先已在上一步完成。"""
    candidates = [Candidate(1, lab_id=2, score=90, obey_cross=True)]
    allocations, talk = plan_adjustments(
        candidates, [], [{'mentor_id': 20, 'lab_id': 2, 'quota_left': 1}]
    )
    assert allocations[0]['student_id'] == 1
    assert allocations[0]['mode'] == 'cross'
    assert talk == []


def test_adjustment_never_oversells_shared_mentor_quota():
    """同一导师同时出现在内部池与跨室池时，名额按导师共享，不得超发。

    回归：曾两次各自扣减同一份 quota_left，导致 1 个名额分出 2 人。
    """
    internal = [{'mentor_id': 10, 'lab_id': 2, 'quota_left': 1}]
    cross = [{'mentor_id': 10, 'lab_id': 2, 'quota_left': 1}]
    candidates = [
        Candidate(1, lab_id=2, score=90, obey_internal=True, obey_cross=True),
        Candidate(2, lab_id=2, score=80, obey_internal=True, obey_cross=True),
    ]
    allocations, talk = plan_adjustments(candidates, internal, cross)

    assigned = [a for a in allocations if a['mentor_id'] == 10]
    assert len(assigned) == 1, f'导师 10 只剩 1 个名额，却分配了 {len(assigned)} 人'
    assert assigned[0]['student_id'] == 1  # 高分优先
    assert [t['student_id'] for t in talk] == [2]


def test_adjustment_shares_quota_across_many_mentors():
    """多个导师的重复出现都应共享名额。"""
    vacancies = [
        {'mentor_id': 10, 'lab_id': 2, 'quota_left': 2},
        {'mentor_id': 20, 'lab_id': 3, 'quota_left': 1},
    ]
    candidates = [
        Candidate(1, lab_id=2, score=99, obey_internal=True, obey_cross=True),
        Candidate(2, lab_id=2, score=98, obey_internal=True, obey_cross=True),
        Candidate(3, lab_id=2, score=97, obey_internal=True, obey_cross=True),
        Candidate(4, lab_id=2, score=96, obey_internal=True, obey_cross=True),
    ]
    allocations, talk = plan_adjustments(candidates, vacancies, vacancies)

    per_mentor: dict[int, int] = {}
    for item in allocations:
        per_mentor[item['mentor_id']] = per_mentor.get(item['mentor_id'], 0) + 1
    assert per_mentor == {10: 2, 20: 1}, per_mentor
    assert len(allocations) == 3
    assert sorted(t['student_id'] for t in talk) == [4]

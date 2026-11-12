"""端到端演示脚本：宣讲 → 填报 → 面试 → 选拔 → 确认 → 补录 → 调剂 → 公示。

直接调用服务层（不经 HTTP），可在无服务器的情况下验证整条业务链路。
用法::

    python scripts/demo_flow.py
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app import models  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.deps import write_audit  # noqa: E402
from app.services import selection_service as service  # noqa: E402


def line(title: str) -> None:
    print(f'\n=== {title} ===')


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.role == models.Role.admin).first()
        students = (
            db.query(models.User)
            .filter(models.User.role == models.Role.student)
            .order_by(models.User.id)
            .all()
        )
        if not admin or not students:
            print('请先运行 python scripts/seed.py')
            return

        intention_round = (
            db.query(models.Round)
            .filter(models.Round.kind == models.RoundKind.intention)
            .order_by(models.Round.id)
            .first()
        )
        if not intention_round:
            print('未找到志愿填报轮次')
            return
        now = utcnow()
        intention_round.starts_at = now - timedelta(days=1)
        intention_round.ends_at = now + timedelta(days=1)
        db.commit()

        line('1. 学生填报平行志愿（最多 3 个）')
        mentors = db.query(models.Mentor).order_by(models.Mentor.id).all()
        for index, student in enumerate(students):
            picks = [mentors[(index + offset) % len(mentors)] for offset in range(3)]
            db.query(models.Intention).filter(
                models.Intention.student_id == student.id
            ).delete(synchronize_session=False)
            for priority, mentor in enumerate(picks, start=1):
                db.add(
                    models.Intention(
                        student_id=student.id,
                        mentor_id=mentor.id,
                        round_id=intention_round.id,
                        priority=priority,
                    )
                )
            print(f'  {student.name}: ' + ' / '.join(m.name for m in picks))
        db.commit()

        line('2. 录入统一面试评分')
        base_scores = [
            (24, 19, 33, 18),
            (22, 17, 30, 16),
            (21, 16, 28, 15),
            (20, 15, 26, 14),
            (19, 14, 24, 13),
            (18, 13, 22, 12),
            (17, 12, 20, 11),
            (16, 11, 18, 10),
        ]
        for index, student in enumerate(students):
            picks = (
                db.query(models.Intention)
                .filter(models.Intention.student_id == student.id)
                .order_by(models.Intention.priority)
                .all()
            )
            for pick in picks:
                scores = base_scores[(index + pick.priority - 1) % len(base_scores)]
                existing = (
                    db.query(models.Interview)
                    .filter(
                        models.Interview.student_id == student.id,
                        models.Interview.mentor_id == pick.mentor_id,
                        models.Interview.round_id == intention_round.id,
                    )
                    .first()
                )
                if not existing:
                    db.add(
                        models.Interview(
                            student_id=student.id,
                            mentor_id=pick.mentor_id,
                            round_id=intention_round.id,
                            score_attitude=scores[0],
                            score_logic=scores[1],
                            score_code=scores[2],
                            score_time=scores[3],
                            scored_by=admin.id,
                        )
                    )
        db.commit()
        print(f'  已录入 {db.query(models.Interview).count()} 条评分')

        line('3. 运行选拔算法')
        result = service.run_selection(
            db,
            round_id=intention_round.id,
            confirm_minutes=120,
            dry_run=False,
            actor=admin,
        )
        print(f'  {result}')

        line('4. 学生确认唯一去向')
        for student in students:
            offers = (
                db.query(models.Offer)
                .filter(
                    models.Offer.student_id == student.id,
                    models.Offer.status == models.OfferStatus.pending,
                )
                .all()
            )
            if not offers:
                print(f'  {student.name}: 无待确认意向')
                continue
            target = sorted(offers, key=lambda o: o.id)[0]
            try:
                service.confirm_offer(
                    db,
                    student=student,
                    mentor_id=target.mentor_id,
                    now=utcnow(),
                    actor=student,
                )
                print(f'  {student.name}: 确认 {target.mentor_id} 号导师')
            except Exception as exc:  # noqa: BLE001
                print(f'  {student.name}: 确认失败 -> {exc}')

        line('5. 逾期释放 + 递补')
        expired = service.expire_offers(db, now=utcnow() + timedelta(hours=3), actor=admin)
        print(f'  释放逾期意向 {expired} 条')
        for mentor in mentors[:3]:
            filled = service.fill_vacancy(
                db, mentor_id=mentor.id, round_id=intention_round.id,
                confirm_minutes=60, actor=admin,
            )
            print(f'  导师 {mentor.name}: {filled}')

        line('6. 统筹调剂')
        adjust = service.adjust(
            db,
            round_id=intention_round.id,
            dry_run=False,
            confirm_minutes=60,
            actor=admin,
        )
        print(f'  内部/跨室调剂 {len(adjust["allocations"])} 人，待约谈 {len(adjust["talk_list"])} 人')

        line('7. 公示与入组')
        pub = models.Publication(
            round_id=intention_round.id,
            title=f'{utcnow().year} 年实训室选组拟录取名单公示',
            content='公示期 1 天，如有异议请通过系统提交实名申诉。',
            status=models.PublicationStatus.published,
            published_at=utcnow(),
            published_by=admin.id,
        )
        db.add(pub)
        db.commit()
        db.refresh(pub)
        write_audit(
            db,
            actor=admin,
            action='create_publication',
            entity='publication',
            entity_id=pub.id,
            after={'title': pub.title, 'status': pub.status.value},
            commit=True,
        )
        print(f'  已发布公示 #{pub.id}')

        confirmed = (
            db.query(models.Offer)
            .filter(models.Offer.status == models.OfferStatus.confirmed)
            .count()
        )
        print(f'\n最终入组人数: {confirmed}')
    finally:
        db.close()


if __name__ == '__main__':
    main()

"""种子数据：一行命令搭好可演示的实训室、导师、轮次、学生与账号。

用法::

    python scripts/seed.py            # 写入（幂等，会先清空业务表）
    python scripts/seed.py --keep     # 保留既有数据，仅补齐缺失项
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app import models  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.demo import DEMO_PASSWORD as demo_password  # noqa: E402
from app.core.security import hash_password  # noqa: E402

DEMO_PASSWORD = demo_password

LABS = [
    {
        'name': '人工智能实训室',
        'capacity': 12,
        'direction': 'AI + PBL',
        'description': '聚焦大模型应用、智能体与工程化落地。',
        'mentors': [
            ('张启明', 4, '具备 Python 基础，能独立完成小型项目。'),
            ('李文博', 4, '对机器学习有热情，愿意长期投入。'),
            ('王思远', 4, '有数据处理或后端开发经验优先。'),
        ],
    },
    {
        'name': '软件开发实训室',
        'capacity': 10,
        'direction': '全栈与工程实践',
        'description': '面向 Web/移动端全栈开发与敏捷协作。',
        'mentors': [
            ('陈慧敏', 5, '熟悉前端框架或后端框架之一。'),
            ('赵鑫', 5, '有团队协作与版本控制经验。'),
        ],
    },
    {
        'name': '嵌入式与物联网实训室',
        'capacity': 8,
        'direction': '嵌入式 / IoT',
        'description': '硬件驱动、传感器网络与边缘计算。',
        'mentors': [
            ('孙一鸣', 4, '了解 C/C++，有单片机开发经历。'),
            ('周宁', 4, '动手能力强，愿意调试硬件。'),
        ],
    },
]

STUDENTS = [
    ('2023001', '陈子墨', True, True),
    ('2023002', '林可欣', True, False),
    ('2023003', '黄俊杰', False, True),
    ('2023004', '刘雨桐', True, True),
    ('2023005', '吴天成', False, False),
    ('2023006', '郑雪儿', True, True),
    ('2023007', '何嘉良', True, False),
    ('2023008', '马晓彤', False, True),
]

STAFF = [
    ('admin', '教务管理员', models.Role.admin),
]


def build_rounds() -> list[models.Round]:
    base = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    plan = [
        ('宣讲会', models.RoundKind.briefing, -2, -2),
        ('开放日', models.RoundKind.open_day, -2, -1),
        ('第一轮志愿填报', models.RoundKind.intention, -1, 0),
        ('第一轮统一面试', models.RoundKind.interview, 0, 0),
        ('拟录取确认', models.RoundKind.confirm, 0, 1),
        ('分轮补录', models.RoundKind.supplement, 1, 3),
        ('统筹调剂', models.RoundKind.adjust, 3, 4),
        ('结果公示', models.RoundKind.publish, 4, 5),
    ]
    return [
        models.Round(
            name=name,
            kind=kind,
            round_no=index + 1,
            starts_at=base + timedelta(days=start),
            ends_at=base + timedelta(days=end, hours=9),
        )
        for index, (name, kind, start, end) in enumerate(plan)
    ]


def seed(keep: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not keep:
            # 用户引用 labs/mentors，必须先删用户再删实训室与导师
            for model in (
                models.AuditLog,
                models.Appeal,
                models.Publication,
                models.Offer,
                models.Interview,
                models.Intention,
                models.User,
                models.Round,
                models.Mentor,
                models.Lab,
            ):
                db.query(model).delete(synchronize_session=False)
            db.commit()

        if db.query(models.Lab).count() > 0:
            print('已存在业务数据，跳过建库（使用 --keep 可重复执行）')
            return

        mentors: list[tuple[models.Lab, models.Mentor]] = []
        for lab_spec in LABS:
            lab = models.Lab(
                name=lab_spec['name'],
                capacity=lab_spec['capacity'],
                direction=lab_spec['direction'],
                description=lab_spec['description'],
                open_day_at=utcnow() + timedelta(days=1),
            )
            db.add(lab)
            db.flush()
            for mentor_name, quota, requirement in lab_spec['mentors']:
                mentor = models.Mentor(
                    lab_id=lab.id,
                    name=mentor_name,
                    quota=quota,
                    requirement=requirement,
                )
                db.add(mentor)
                db.flush()
                mentors.append((lab, mentor))

        for no, name, role in STAFF:
            db.add(
                models.User(
                    student_no=no,
                    name=name,
                    role=role,
                    password_hash=hash_password(DEMO_PASSWORD),
                )
            )

        for no, name, obey_internal, obey_cross in STUDENTS:
            db.add(
                models.User(
                    student_no=no,
                    name=name,
                    role=models.Role.student,
                    password_hash=hash_password(DEMO_PASSWORD),
                    obey_internal=obey_internal,
                    obey_cross=obey_cross,
                )
            )

        for index, (lab, mentor) in enumerate(mentors, start=1):
            db.add(
                models.User(
                    student_no=f't{1000 + index}',
                    name=mentor.name,
                    role=models.Role.mentor,
                    password_hash=hash_password(DEMO_PASSWORD),
                    lab_id=lab.id,
                    mentor_id=mentor.id,
                )
            )

        for round_obj in build_rounds():
            db.add(round_obj)

        db.commit()
        print('种子数据写入完成')
        print(f'  演示账号密码统一为: {DEMO_PASSWORD}')
        print('  管理员: admin')
        print(f'  老师: t1001 ~ t{1000 + len(mentors)}')
        print('  学生: 2023001 ~ 2023008')
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='写入演示种子数据')
    parser.add_argument('--keep', action='store_true', help='保留既有数据')
    args = parser.parse_args()
    seed(keep=args.keep)

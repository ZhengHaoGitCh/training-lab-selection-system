from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.clock import utcnow
from .core.database import Base


class Role(str, enum.Enum):
    student = 'student'
    mentor = 'mentor'
    admin = 'admin'


class Decision(str, enum.Enum):
    proposed = 'proposed'
    waitlist = 'waitlist'
    internal_candidate = 'internal_candidate'
    rejected = 'rejected'


class OfferStatus(str, enum.Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    rejected = 'rejected'
    expired = 'expired'


class OfferType(str, enum.Enum):
    regular = 'regular'
    supplement = 'supplement'
    internal = 'internal'
    cross = 'cross'
    assigned = 'assigned'


class RoundKind(str, enum.Enum):
    briefing = 'briefing'
    open_day = 'open_day'
    intention = 'intention'
    interview = 'interview'
    confirm = 'confirm'
    supplement = 'supplement'
    adjust = 'adjust'
    publish = 'publish'


class AppealStatus(str, enum.Enum):
    open = 'open'
    accepted = 'accepted'
    rejected = 'rejected'
    closed = 'closed'


class PublicationStatus(str, enum.Enum):
    draft = 'draft'
    published = 'published'
    closed = 'closed'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    student_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.student, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default='')
    email: Mapped[str] = mapped_column(String(128), default='')
    phone: Mapped[str] = mapped_column(String(32), default='')
    lab_id: Mapped[int | None] = mapped_column(ForeignKey('labs.id'), nullable=True)
    mentor_id: Mapped[int | None] = mapped_column(ForeignKey('mentors.id'), nullable=True)
    obey_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    obey_cross: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Lab(Base):
    __tablename__ = 'labs'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[str] = mapped_column(String(128), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    open_day_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    mentors: Mapped[list['Mentor']] = relationship(
        back_populates='lab', cascade='all, delete-orphan'
    )


class Mentor(Base):
    __tablename__ = 'mentors'

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey('labs.id'), index=True)
    name: Mapped[str] = mapped_column(String(64))
    quota: Mapped[int] = mapped_column(Integer, default=0)
    requirement: Mapped[str] = mapped_column(Text, default='')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lab: Mapped[Lab] = relationship(back_populates='mentors')


class Round(Base):
    __tablename__ = 'rounds'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[RoundKind] = mapped_column(SAEnum(RoundKind), default=RoundKind.intention, index=True)
    round_no: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Intention(Base):
    __tablename__ = 'intentions'
    __table_args__ = (
        UniqueConstraint('student_id', 'mentor_id', 'round_id', name='uq_intention'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey('mentors.id'), index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey('rounds.id'), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Interview(Base):
    __tablename__ = 'interviews'
    __table_args__ = (
        UniqueConstraint('student_id', 'mentor_id', 'round_id', name='uq_interview'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey('mentors.id'), index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey('rounds.id'), index=True)
    score_attitude: Mapped[int] = mapped_column(Integer, default=0)
    score_logic: Mapped[int] = mapped_column(Integer, default=0)
    score_code: Mapped[int] = mapped_column(Integer, default=0)
    score_time: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[Decision] = mapped_column(SAEnum(Decision), default=Decision.rejected)
    remark: Mapped[str] = mapped_column(Text, default='')
    scored_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Offer(Base):
    __tablename__ = 'offers'

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey('mentors.id'), index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey('rounds.id'), index=True)
    offer_type: Mapped[OfferType] = mapped_column(SAEnum(OfferType), default=OfferType.regular)
    status: Mapped[OfferStatus] = mapped_column(SAEnum(OfferStatus), default=OfferStatus.pending, index=True)
    reason: Mapped[str] = mapped_column(String(255), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Publication(Base):
    __tablename__ = 'publications'

    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int | None] = mapped_column(ForeignKey('rounds.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[PublicationStatus] = mapped_column(
        SAEnum(PublicationStatus), default=PublicationStatus.draft
    )
    published_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Appeal(Base):
    __tablename__ = 'appeals'

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    publication_id: Mapped[int | None] = mapped_column(ForeignKey('publications.id'), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[AppealStatus] = mapped_column(SAEnum(AppealStatus), default=AppealStatus.open)
    reply: Mapped[str] = mapped_column(Text, default='')
    handled_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(64), default='system')
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(64), default='')
    entity_id: Mapped[int] = mapped_column(Integer, default=0)
    before_json: Mapped[str] = mapped_column(Text, default='')
    after_json: Mapped[str] = mapped_column(Text, default='')
    ip: Mapped[str] = mapped_column(String(64), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

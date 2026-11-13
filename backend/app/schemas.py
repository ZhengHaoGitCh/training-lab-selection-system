from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    AppealStatus,
    Decision,
    OfferStatus,
    OfferType,
    PublicationStatus,
    Role,
    RoundKind,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    total: int
    limit: int
    offset: int


# ---------- 鉴权 ----------


class RegisterIn(BaseModel):
    student_no: str = Field(min_length=3, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: str = ''
    phone: str = ''


class LoginIn(BaseModel):
    student_no: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class AdminCreateUserIn(BaseModel):
    student_no: str = Field(min_length=3, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: Role = Role.student
    lab_id: int | None = None
    email: str = ''
    phone: str = ''


class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int
    user: 'UserOut'


class UserOut(ORMModel):
    id: int
    student_no: str
    name: str
    role: Role
    email: str = ''
    lab_id: int | None = None
    mentor_id: int | None = None
    obey_internal: bool
    obey_cross: bool
    is_active: bool
    created_at: datetime


# ---------- 基础数据 ----------


class LabIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    capacity: int = Field(ge=0, le=1000)
    direction: str = ''
    description: str = ''
    open_day_at: datetime | None = None


class LabPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    capacity: int | None = Field(default=None, ge=0, le=1000)
    direction: str | None = None
    description: str | None = None
    open_day_at: datetime | None = None


class LabOut(ORMModel):
    id: int
    name: str
    capacity: int
    direction: str
    description: str
    open_day_at: datetime | None
    mentor_count: int = 0
    quota_total: int = 0


class MentorIn(BaseModel):
    lab_id: int
    name: str = Field(min_length=1, max_length=64)
    quota: int = Field(ge=0, le=1000)
    requirement: str = ''


class MentorPatch(BaseModel):
    lab_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=64)
    quota: int | None = Field(default=None, ge=0, le=1000)
    requirement: str | None = None
    is_active: bool | None = None


class MentorOut(ORMModel):
    id: int
    lab_id: int
    name: str
    quota: int
    requirement: str
    is_active: bool
    lab_name: str = ''
    quota_taken: int = 0


class RoundIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    kind: RoundKind = RoundKind.intention
    round_no: int = Field(default=1, ge=1, le=10)
    starts_at: datetime
    ends_at: datetime

    @field_validator('ends_at')
    @classmethod
    def _check_range(cls, value: datetime, info):  # noqa: ANN001
        start = info.data.get('starts_at')
        if start and value <= start:
            raise ValueError('ends_at 必须晚于 starts_at')
        return value


class RoundPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    kind: RoundKind | None = None
    round_no: int | None = Field(default=None, ge=1, le=10)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator('ends_at')
    @classmethod
    def _check_range(cls, value: datetime | None, info):  # noqa: ANN001
        start = info.data.get('starts_at')
        if start and value and value <= start:
            raise ValueError('ends_at 必须晚于 starts_at')
        return value


class RoundOut(ORMModel):
    id: int
    name: str
    kind: RoundKind
    round_no: int
    starts_at: datetime
    ends_at: datetime
    is_open: bool = False


# ---------- 学生流程 ----------


class IntentionIn(BaseModel):
    mentor_ids: list[int] = Field(min_length=1, max_length=3)
    round_id: int
    obey_internal: bool = False
    obey_cross: bool = False

    @field_validator('mentor_ids')
    @classmethod
    def _unique(cls, value: list[int]):
        if len(set(value)) != len(value):
            raise ValueError('志愿导师不能重复')
        return value


class IntentionOut(ORMModel):
    id: int
    student_id: int
    mentor_id: int
    round_id: int
    priority: int
    created_at: datetime
    mentor_name: str = ''
    lab_name: str = ''


class InterviewIn(BaseModel):
    student_id: int
    mentor_id: int
    round_id: int
    score_attitude: int = Field(ge=0, le=25)
    score_logic: int = Field(ge=0, le=20)
    score_code: int = Field(ge=0, le=35)
    score_time: int = Field(ge=0, le=20)
    remark: str = ''


class InterviewOut(ORMModel):
    id: int
    student_id: int
    mentor_id: int
    round_id: int
    score_attitude: int
    score_logic: int
    score_code: int
    score_time: int
    total_score: int = 0
    decision: Decision
    remark: str
    student_name: str = ''
    mentor_name: str = ''


class TeacherInterviewIn(BaseModel):
    student_id: int
    round_id: int
    score_attitude: int = Field(ge=0, le=25)
    score_logic: int = Field(ge=0, le=20)
    score_code: int = Field(ge=0, le=35)
    score_time: int = Field(ge=0, le=20)
    remark: str = ''


class RunSelectionIn(BaseModel):
    round_id: int
    confirm_minutes: int = Field(default=120, ge=1, le=10080)
    dry_run: bool = False


class RunSelectionOut(BaseModel):
    round_id: int
    proposed: int
    waitlist: int
    internal_candidate: int
    rejected: int
    offers_created: int
    offers_skipped: int
    dry_run: bool = False


class ConfirmIn(BaseModel):
    mentor_id: int | None = None


class OfferOut(ORMModel):
    id: int
    student_id: int
    mentor_id: int
    round_id: int
    offer_type: OfferType
    status: OfferStatus
    reason: str
    created_at: datetime
    expires_at: datetime | None
    confirmed_at: datetime | None
    mentor_name: str = ''
    lab_name: str = ''


class FillVacancyIn(BaseModel):
    round_id: int | None = None
    confirm_minutes: int = Field(default=120, ge=1, le=10080)


class AdjustIn(BaseModel):
    round_id: int
    dry_run: bool = False
    confirm_minutes: int = Field(default=120, ge=1, le=10080)


class AdjustAllocationOut(BaseModel):
    student_id: int
    mentor_id: int
    lab_id: int
    mode: str


class AdjustOut(BaseModel):
    allocations: list[AdjustAllocationOut]
    talk_list: list[dict]
    offers_created: int


class AssignTalkIn(BaseModel):
    student_id: int
    mentor_id: int
    round_id: int
    reason: str = '统筹安置'


# ---------- 公示与申诉 ----------


class PublicationIn(BaseModel):
    round_id: int | None = None
    title: str = Field(min_length=1, max_length=128)
    content: str = ''


class PublicationOut(ORMModel):
    id: int
    round_id: int | None
    title: str
    content: str
    status: PublicationStatus
    published_at: datetime | None
    created_at: datetime


class AppealIn(BaseModel):
    publication_id: int | None = None
    content: str = Field(min_length=5, max_length=2000)


class AppealHandleIn(BaseModel):
    status: AppealStatus
    reply: str = Field(min_length=1, max_length=2000)


class AppealOut(ORMModel):
    id: int
    student_id: int
    publication_id: int | None
    content: str
    status: AppealStatus
    reply: str
    created_at: datetime
    handled_at: datetime | None
    student_name: str = ''


class AuditLogOut(ORMModel):
    id: int
    actor: str
    actor_id: int | None
    action: str
    entity: str
    entity_id: int
    before_json: str
    after_json: str
    ip: str
    created_at: datetime


class DashboardOut(BaseModel):
    labs: int
    mentors: int
    quota_total: int
    students: int
    intentions: int
    interviews: int
    offers_pending: int
    offers_confirmed: int
    enrolled: int
    rounds_open: list[str]


TokenOut.model_rebuild()

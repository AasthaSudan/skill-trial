from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, now, uid

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default='candidate')
    status: Mapped[str] = mapped_column(String, default='active')
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped[dict] = mapped_column(JSON, default=lambda: {'timezone': 'Asia/Kolkata', 'roles': [], 'headline': '', 'goal': '', 'onboarded': False})
    preferences: Mapped[dict] = mapped_column(JSON, default=lambda: {'gamification': True, 'celebrations': 'subtle', 'theme': 'observatory', 'sounds': False, 'notify_quest_reminders': False, 'notify_weekly_recap': False, 'resume_retention_days': 0, 'ai_resume_extraction': False, 'ai_explanation_feedback': False})
    failures: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[float] = mapped_column(Float, default=0)
    delete_at: Mapped[float | None] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float, default=now)

class AuthSession(Base):
    __tablename__ = 'sessions'
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    csrf: Mapped[str] = mapped_column(String)
    created: Mapped[float] = mapped_column(Float, default=now)
    seen: Mapped[float] = mapped_column(Float, default=now)

class Token(Base):
    __tablename__ = 'auth_tokens'
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    kind: Mapped[str] = mapped_column(String)
    expires: Mapped[float] = mapped_column(Float)

class Resume(Base):
    __tablename__ = 'resumes'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    filename: Mapped[str] = mapped_column(String)
    digest: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='uploaded')
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[float] = mapped_column(Float, default=now)

class Claim(Base):
    __tablename__ = 'claims'
    __table_args__ = (UniqueConstraint('user_id', 'skill'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    resume_id: Mapped[str | None] = mapped_column(ForeignKey('resumes.id', ondelete='SET NULL'))
    skill: Mapped[str] = mapped_column(String)
    level: Mapped[str | None] = mapped_column(String)
    original_level: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='pending_review')
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=1)
    source: Mapped[str] = mapped_column(String, default='manual')

class Challenge(Base):
    __tablename__ = 'challenges'
    __table_args__ = (UniqueConstraint('slug', 'version'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    skill: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)
    pool: Mapped[str] = mapped_column(String, default='assessment')
    family: Mapped[str] = mapped_column(String)
    level: Mapped[str] = mapped_column(String, default='intermediate')
    status: Mapped[str] = mapped_column(String, default='draft')
    author: Mapped[str] = mapped_column(String, default='seed')
    reviewer: Mapped[str | None] = mapped_column(String)
    content: Mapped[dict] = mapped_column(JSON)
    validation: Mapped[dict] = mapped_column(JSON, default=dict)

class Attempt(Base):
    __tablename__ = 'attempts'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    skill: Mapped[str] = mapped_column(String)
    level: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String, default='formal')
    claim_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    policy: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default='created')
    duration: Mapped[int] = mapped_column(Integer)
    started: Mapped[float | None] = mapped_column(Float)
    deadline: Mapped[float | None] = mapped_column(Float)
    completed: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(String)
    result: Mapped[dict | None] = mapped_column(JSON)
    report_hash: Mapped[str | None] = mapped_column(String)
    created: Mapped[float] = mapped_column(Float, default=now)

class Item(Base):
    __tablename__ = 'items'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    attempt_id: Mapped[str] = mapped_column(ForeignKey('attempts.id', ondelete='CASCADE'), index=True)
    challenge_id: Mapped[str] = mapped_column(ForeignKey('challenges.id'))
    ordinal: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default='not_started')
    draft: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    saved: Mapped[float | None] = mapped_column(Float)
    submission: Mapped[dict | None] = mapped_column(JSON)
    evaluation: Mapped[dict | None] = mapped_column(JSON)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    last_run: Mapped[float] = mapped_column(Float, default=0)
    hints: Mapped[int] = mapped_column(Integer, default=0)

class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default='queued', index=True)
    tries: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[float] = mapped_column(Float, default=now)
    error: Mapped[str | None] = mapped_column(String)

class XP(Base):
    __tablename__ = 'xp_ledger'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    points: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default='')
    created: Mapped[float] = mapped_column(Float, default=now)

class Activity(Base):
    __tablename__ = 'activities'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(String)
    facts: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[float] = mapped_column(Float, default=now)

class Path(Base):
    __tablename__ = 'learning_paths'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    attempt_id: Mapped[str] = mapped_column(String, unique=True)
    skill: Mapped[str] = mapped_column(String)
    items: Mapped[list] = mapped_column(JSON)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=now)

class LearningResource(Base):
    __tablename__ = 'learning_resources'
    __table_args__ = (UniqueConstraint('slug', 'version'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    skill: Mapped[str] = mapped_column(String, index=True)
    competency: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    question: Mapped[str] = mapped_column(String)
    options: Mapped[list] = mapped_column(JSON)
    answer: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default='draft')
    validation: Mapped[dict] = mapped_column(JSON, default=dict)
    author: Mapped[str] = mapped_column(String, default='system')
    reviewer: Mapped[str | None] = mapped_column(String)
    created: Mapped[float] = mapped_column(Float, default=now)

class BadgeDefinition(Base):
    __tablename__ = 'badge_definitions'
    slug: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    icon: Mapped[str] = mapped_column(String, default='Award')
    metric: Mapped[str] = mapped_column(String)
    thresholds: Mapped[list] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    author: Mapped[str] = mapped_column(String, default='system')
    created: Mapped[float] = mapped_column(Float, default=now)
    updated: Mapped[float] = mapped_column(Float, default=now)

class BadgeAward(Base):
    __tablename__ = 'badge_awards'
    __table_args__ = (UniqueConstraint('user_id', 'badge_slug', 'tier'),)
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    badge_slug: Mapped[str] = mapped_column(ForeignKey('badge_definitions.slug'), index=True)
    tier: Mapped[int] = mapped_column(Integer)
    rule_version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    source: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=now)

class Quest(Base):
    __tablename__ = 'quests'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    target: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)

class Celebration(Base):
    __tablename__ = 'celebrations'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    tier: Mapped[int] = mapped_column(Integer, default=1)
    seen: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=now)

class InboxNotification(Base):
    __tablename__ = 'inbox_notifications'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(String, default='update')
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String, default='/app')
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created: Mapped[float] = mapped_column(Float, default=now)

class OrbitProgress(Base):
    __tablename__ = 'orbit_progress'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    skill: Mapped[str] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[float] = mapped_column(Float, default=now)

class Notice(Base):
    __tablename__ = 'notification_outbox'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default='queued', index=True)
    created: Mapped[float] = mapped_column(Float, default=now)
    delivered: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(String)

class ReportShare(Base):
    __tablename__ = 'report_shares'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    token_hint: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    label: Mapped[str] = mapped_column(String, default='')
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    expires: Mapped[float] = mapped_column(Float)
    revoked: Mapped[float | None] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float, default=now)
    last_accessed: Mapped[float | None] = mapped_column(Float)
    access_count: Mapped[int] = mapped_column(Integer, default=0)

class LeagueMember(Base):
    __tablename__ = 'league_members'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    alias: Mapped[str] = mapped_column(String, unique=True)
    joined: Mapped[float] = mapped_column(Float, default=now)

class ReportShareItem(Base):
    __tablename__ = 'report_share_items'
    __table_args__ = (UniqueConstraint('share_id', 'attempt_id'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    share_id: Mapped[str] = mapped_column(ForeignKey('report_shares.id', ondelete='CASCADE'), index=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey('attempts.id', ondelete='CASCADE'), index=True)

class ShareAccess(Base):
    __tablename__ = 'share_access_logs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    share_id: Mapped[str | None] = mapped_column(ForeignKey('report_shares.id', ondelete='SET NULL'), index=True)
    outcome: Mapped[str] = mapped_column(String)
    created: Mapped[float] = mapped_column(Float, default=now)

class AppSetting(Base):
    __tablename__ = 'app_settings'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_by: Mapped[str] = mapped_column(String, default='system')
    updated: Mapped[float] = mapped_column(Float, default=now)

class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String, default='')
    created: Mapped[float] = mapped_column(Float, default=now)

class Idempotency(Base):
    __tablename__ = 'idempotency'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    digest: Mapped[str] = mapped_column(String)
    response: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=now)

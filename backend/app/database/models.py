import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships with cascade delete for tenant data purging
    profile: Mapped[Optional["UserProfile"]] = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    provider_config: Mapped[Optional["ProviderConfig"]] = relationship("ProviderConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes: Mapped[List["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    job_descriptions: Mapped[List["JobDescription"]] = relationship("JobDescription", back_populates="user", cascade="all, delete-orphan")
    interviews: Mapped[List["Interview"]] = relationship("Interview", back_populates="user", cascade="all, delete-orphan")
    plans: Mapped[List["Plan"]] = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
    coding_submissions: Mapped[List["CodingSubmission"]] = relationship("CodingSubmission", back_populates="user", cascade="all, delete-orphan")
    skills: Mapped[List["UserSkill"]] = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    target_role: Mapped[str] = mapped_column(String(100), default="Software Engineer")
    years_experience: Mapped[float] = mapped_column(Float, default=0.0)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, default=45)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="profile")

class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(50), default="mock")  # 'bedrock', 'mock'
    aws_region: Mapped[str] = mapped_column(String(50), default="us-east-1")
    aws_access_key_masked: Mapped[str] = mapped_column(String(50), default="")
    aws_secret_key_enc: Mapped[str] = mapped_column(Text, default="")
    preferred_model: Mapped[str] = mapped_column(String(100), default="qwen.qwen3-32b-instruct-v1:0")
    default_model: Mapped[Optional[str]] = mapped_column(String(100), default="qwen.qwen3-32b-instruct-v1:0", nullable=True)
    interviewer_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evaluation_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    coding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    planning_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fallback_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_token_budget: Mapped[int] = mapped_column(Integer, default=1_000_000)
    monthly_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    monthly_cost_cents_budget: Mapped[int] = mapped_column(Integer, default=1000)  # $10.00
    monthly_cost_cents_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="provider_config")

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    extracted_text: Mapped[str] = mapped_column(Text)
    extracted_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    projects_context: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="resumes")

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="Software Engineer")
    company: Mapped[str] = mapped_column(String(200), default="")
    raw_text: Mapped[str] = mapped_column(Text)
    extracted_role: Mapped[str] = mapped_column(String(200), default="")
    extracted_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    extracted_requirements: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="job_descriptions")

class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(20))  # 'domain' or 'jd'
    category: Mapped[str] = mapped_column(String(30))  # 'technical', 'behavioral', 'dsa', 'managerial'
    title: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[str] = mapped_column(String(150), default="Software Engineer")
    difficulty: Mapped[str] = mapped_column(String(20), default="intermediate")
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # 'in_progress', 'completed', 'cancelled'
    domain_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    jd_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True)
    resume_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    target_duration_minutes: Mapped[int] = mapped_column(Integer, default=20)
    hint_level_used: Mapped[int] = mapped_column(Integer, default=0)
    coding_problem_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_summary: Mapped[str] = mapped_column(Text, default="")
    covered_topics: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="interviews")
    messages: Mapped[List["InterviewMessage"]] = relationship("InterviewMessage", back_populates="interview", cascade="all, delete-orphan", order_by="InterviewMessage.created_at")
    self_evaluation: Mapped[Optional["SelfEvaluation"]] = relationship("SelfEvaluation", back_populates="interview", uselist=False, cascade="all, delete-orphan")
    ai_evaluation: Mapped[Optional["Evaluation"]] = relationship("Evaluation", back_populates="interview", uselist=False, cascade="all, delete-orphan")

class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # 'assistant', 'user', 'system'
    content: Mapped[str] = mapped_column(Text)
    question_index: Mapped[int] = mapped_column(Integer, default=0)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    interview: Mapped["Interview"] = relationship("Interview", back_populates="messages")

class SelfEvaluation(Base):
    __tablename__ = "self_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    dimension_scores: Mapped[Dict[str, int]] = mapped_column(JSON, default=dict)  # dimension: 1-5 score
    question_evaluations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    reflection: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    interview: Mapped["Interview"] = relationship("Interview", back_populates="self_evaluation")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    overall_score: Mapped[float] = mapped_column(Float)  # 0.0 to 100.0
    rubric_dimension_scores: Mapped[Dict[str, Dict[str, Any]]] = mapped_column(JSON, default=dict)  # {dim: {score, max, explanation, evidence_quote}}
    strengths: Mapped[List[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_concepts: Mapped[List[str]] = mapped_column(JSON, default=list)
    evidence_excerpts: Mapped[List[Dict[str, str]]] = mapped_column(JSON, default=list)
    question_feedback: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    suggested_corrections: Mapped[List[str]] = mapped_column(JSON, default=list)
    uncertainty_notes: Mapped[List[str]] = mapped_column(JSON, default=list)
    raw_llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    model_identifier: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    interview: Mapped["Interview"] = relationship("Interview", back_populates="ai_evaluation")
    plan: Mapped[Optional["Plan"]] = relationship("Plan", back_populates="evaluation", uselist=False)

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    evaluation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evaluations.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[str] = mapped_column(String(150), default="Software Engineer")
    target_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")  # 'active', 'completed', 'archived'
    total_days: Mapped[int] = mapped_column(Integer, default=7)
    current_day: Mapped[int] = mapped_column(Integer, default=1)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, default=45)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="plans")
    evaluation: Mapped[Optional["Evaluation"]] = relationship("Evaluation", back_populates="plan")
    tasks: Mapped[List["PlanTask"]] = relationship("PlanTask", back_populates="plan", cascade="all, delete-orphan", order_by="PlanTask.day_number")

class PlanTask(Base):
    __tablename__ = "plan_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    day_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(30), default="practice")  # 'concept', 'practice', 'coding', 'reassessment'
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    external_resources: Mapped[List[Dict[str, str]]] = mapped_column(JSON, default=list)  # [{title, url, type}]
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="tasks")

class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    interview_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("interviews.id", ondelete="SET NULL"), nullable=True)
    problem_title: Mapped[str] = mapped_column(String(200), default="Coding Challenge")
    language: Mapped[str] = mapped_column(String(20))  # 'python', 'java', 'cpp'
    code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))  # 'passed', 'failed', 'timeout', 'compile_error', 'runtime_error'
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    memory_kb: Mapped[int] = mapped_column(Integer, default=0)
    tests_passed: Mapped[int] = mapped_column(Integer, default=0)
    tests_total: Mapped[int] = mapped_column(Integer, default=0)
    test_results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="coding_submissions")

class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_user_skills_user_topic"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    evidence_refs: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="skills")

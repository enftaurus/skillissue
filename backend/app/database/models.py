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

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    users: Mapped[List["User"]] = relationship("User", back_populates="tenant")

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="candidate")  # 'candidate', 'recruiter', 'admin'
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships with cascade delete for tenant data purging
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="users")
    profile: Mapped[Optional["UserProfile"]] = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    provider_config: Mapped[Optional["ProviderConfig"]] = relationship("ProviderConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes: Mapped[List["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    job_descriptions: Mapped[List["JobDescription"]] = relationship("JobDescription", back_populates="user", cascade="all, delete-orphan")
    interviews: Mapped[List["Interview"]] = relationship("Interview", back_populates="user", cascade="all, delete-orphan")
    plans: Mapped[List["Plan"]] = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
    coding_submissions: Mapped[List["CodingSubmission"]] = relationship("CodingSubmission", back_populates="user", cascade="all, delete-orphan")
    project_submissions: Mapped[List["ProjectSubmission"]] = relationship("ProjectSubmission", back_populates="user", cascade="all, delete-orphan")
    skills: Mapped[List["UserSkill"]] = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    backlog_items: Mapped[List["LearningBacklogItem"]] = relationship("LearningBacklogItem", back_populates="user", cascade="all, delete-orphan")
    company_progress: Mapped[List["UserCompanyProgress"]] = relationship("UserCompanyProgress", back_populates="user", cascade="all, delete-orphan")
    retest_sessions: Mapped[List["RetestSession"]] = relationship("RetestSession", back_populates="user", cascade="all, delete-orphan")
    assessment_pipelines: Mapped[List["AssessmentPipeline"]] = relationship("AssessmentPipeline", back_populates="creator", cascade="all, delete-orphan")
    explanation_checks: Mapped[List["ExplanationCheck"]] = relationship("ExplanationCheck", back_populates="user", cascade="all, delete-orphan")

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
    azure_endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    azure_api_version: Mapped[Optional[str]] = mapped_column(String(50), default="2024-06-01", nullable=True)
    azure_deployment_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    preferred_model: Mapped[str] = mapped_column(String(100), default="qwen.qwen3-32b-v1:0")
    default_model: Mapped[Optional[str]] = mapped_column(String(100), default="qwen.qwen3-32b-v1:0", nullable=True)
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
    config_version: Mapped[int] = mapped_column(Integer, default=1)
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
    latest_submission_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    current_summary: Mapped[str] = mapped_column(Text, default="")
    covered_topics: Mapped[List[str]] = mapped_column(JSON, default=list)
    topic_statuses: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
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
    client_turn_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
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
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 100.0 or None
    status: Mapped[str] = mapped_column(String(30), default="completed")  # 'completed', 'not_evaluated'
    rubric_dimension_scores: Mapped[Dict[str, Dict[str, Any]]] = mapped_column(JSON, default=dict)  # {dim: {score, max, explanation, evidence_quote}}
    strengths: Mapped[List[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[List[str]] = mapped_column(JSON, default=list)
    missing_concepts: Mapped[List[str]] = mapped_column(JSON, default=list)
    evidence_excerpts: Mapped[List[Dict[str, str]]] = mapped_column(JSON, default=list)
    question_feedback: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    suggested_corrections: Mapped[List[str]] = mapped_column(JSON, default=list)
    uncertainty_notes: Mapped[List[str]] = mapped_column(JSON, default=list)
    weakness_analysis: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    raw_llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stored_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    topic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    goal: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 'fundamentals', 'interview_prep', 'mastery'
    target_role: Mapped[str] = mapped_column(String(150), default="Software Engineer")
    target_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    schedule_days: Mapped[List[str]] = mapped_column(JSON, default=list)  # e.g. ["monday", "wednesday", "friday"]
    current_level: Mapped[str] = mapped_column(String(30), default="intermediate")  # 'beginner', 'intermediate', 'advanced'
    status: Mapped[str] = mapped_column(String(20), default="active")  # 'active', 'completed', 'archived'
    total_days: Mapped[int] = mapped_column(Integer, default=7)
    current_day: Mapped[int] = mapped_column(Integer, default=1)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, default=45)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    subtopic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    task_type: Mapped[str] = mapped_column(String(30), default="practice")  # 'concept', 'practice', 'coding', 'reassessment'
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="upcoming")  # 'upcoming', 'in_progress', 'completed', 'skipped'
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

class LearningBacklogItem(Base):
    __tablename__ = "learning_backlog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    subtopic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # 'interview_evaluation', 'manual', 'coding_practice'
    source_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # e.g. interview_id
    reason: Mapped[str] = mapped_column(Text, default="")
    learning_objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_exercise: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # 'low', 'medium', 'high'
    status: Mapped[str] = mapped_column(String(30), default="queued")  # 'queued', 'planned', 'in_progress', 'completed', 'dismissed'
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    planned_plan_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="backlog_items")
    plan: Mapped[Optional["Plan"]] = relationship("Plan")

class ProjectSubmission(Base):
    __tablename__ = "project_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(30), default="incomplete")
    files: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    test_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    prompt_analysis: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    prompts_count: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="project_submissions")

class CompanyTrack(Base):
    __tablename__ = "company_tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="gold")  # 'gold', 'silver', 'bronze'
    role_title: Mapped[str] = mapped_column(String(150), default="Software Development Engineer")
    description: Mapped[str] = mapped_column(Text, default="")
    community_tips: Mapped[List[str]] = mapped_column(JSON, default=list)  # Curated from community experiences
    total_problems: Mapped[int] = mapped_column(Integer, default=0)
    initial_unlocked_count: Mapped[int] = mapped_column(Integer, default=3)
    logo_icon: Mapped[str] = mapped_column(String(50), default="Building2")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    problems: Mapped[List["CompanyProblem"]] = relationship("CompanyProblem", back_populates="track", cascade="all, delete-orphan")
    progress: Mapped[List["UserCompanyProgress"]] = relationship("UserCompanyProgress", back_populates="track", cascade="all, delete-orphan")

class CompanyProblem(Base):
    __tablename__ = "company_problems"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_track_id: Mapped[str] = mapped_column(String(36), ForeignKey("company_tracks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # 'EASY', 'MEDIUM', 'HARD'
    frequency_score: Mapped[float] = mapped_column(Float, default=100.0)
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.5)
    topics: Mapped[List[str]] = mapped_column(JSON, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    is_initially_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")
    starter_code: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    test_cases: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    track: Mapped["CompanyTrack"] = relationship("CompanyTrack", back_populates="problems")

    @property
    def leetcode_url(self) -> str:
        return f"https://leetcode.com/problems/{self.slug}/"

class UserCompanyProgress(Base):
    __tablename__ = "user_company_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "company_track_id", name="uq_user_company_progress"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_track_id: Mapped[str] = mapped_column(String(36), ForeignKey("company_tracks.id", ondelete="CASCADE"), index=True)
    unlocked_count: Mapped[int] = mapped_column(Integer, default=3)
    solved_count: Mapped[int] = mapped_column(Integer, default=0)
    solved_problem_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    last_practiced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="company_progress")
    track: Mapped["CompanyTrack"] = relationship("CompanyTrack", back_populates="progress")

class RetestSession(Base):
    __tablename__ = "retest_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_interview_id: Mapped[str] = mapped_column(String(36), ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    original_evaluation_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True)
    retest_interview_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("interviews.id", ondelete="SET NULL"), nullable=True)
    weakness_topic: Mapped[str] = mapped_column(String(150), nullable=False)
    baseline_score: Mapped[float] = mapped_column(Float, default=0.0)
    retest_score: Mapped[float] = mapped_column(Float, default=0.0)
    delta_score: Mapped[float] = mapped_column(Float, default=0.0)
    verified_improvements: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # 'pending', 'in_progress', 'completed'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="retest_sessions")
    original_interview: Mapped["Interview"] = relationship("Interview", foreign_keys=[original_interview_id])
    original_evaluation: Mapped["Evaluation"] = relationship("Evaluation", foreign_keys=[original_evaluation_id])

class AssessmentPipeline(Base):
    __tablename__ = "assessment_pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_role: Mapped[str] = mapped_column(String(150), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    rounds: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    oa_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=lambda: {"mode": "preset", "custom_url": "", "rating_min": 1200, "rating_max": 1600, "topic_tags": ["dp", "graphs"]})
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invite_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    creator: Mapped["User"] = relationship("User", back_populates="assessment_pipelines")
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant")
    candidates: Mapped[List["CandidateAssessment"]] = relationship("CandidateAssessment", back_populates="pipeline", cascade="all, delete-orphan")

class CandidateAssessment(Base):
    __tablename__ = "candidate_assessments"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "candidate_email", name="uq_candidate_assessment_pipeline_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("assessment_pipelines.id", ondelete="CASCADE"), index=True)
    candidate_name: Mapped[str] = mapped_column(String(150), nullable=False)
    candidate_email: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="invited")  # 'invited', 'in_progress', 'completed', 'flagged'
    resume_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    oa_problem_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    oa_submitted_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_round_index: Mapped[int] = mapped_column(Integer, default=0)
    round_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    composite_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    integrity_signals: Mapped[Dict[str, Any]] = mapped_column(JSON, default=lambda: {"status": "not_assessed"})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    pipeline: Mapped["AssessmentPipeline"] = relationship("AssessmentPipeline", back_populates="candidates")
    explanation_checks: Mapped[List["ExplanationCheck"]] = relationship("ExplanationCheck", back_populates="candidate_assessment", cascade="all, delete-orphan")
    editor_event_batches: Mapped[List["EditorEventBatch"]] = relationship("EditorEventBatch", back_populates="candidate_assessment", cascade="all, delete-orphan")


class ExplanationCheck(Base):
    __tablename__ = "explanation_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    candidate_assessment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("candidate_assessments.id", ondelete="CASCADE"), nullable=True, index=True)
    round_key: Mapped[str] = mapped_column(String(50), default="oa_dsa")
    submission_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="practice")  # 'practice', 'assessment'
    status: Mapped[str] = mapped_column(String(30), default="pending")  # 'pending', 'answered', 'evaluated', 'not_evaluated', 'insufficient_data'
    questions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    answers: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    evaluation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'low', 'medium', 'high', None
    discriminative_power: Mapped[str] = mapped_column(String(20), default="normal")  # 'low', 'normal'
    model_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="explanation_checks")
    candidate_assessment: Mapped[Optional["CandidateAssessment"]] = relationship("CandidateAssessment", back_populates="explanation_checks")


class EditorEventBatch(Base):
    __tablename__ = "editor_event_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_assessments.id", ondelete="CASCADE"), index=True)
    round_key: Mapped[str] = mapped_column(String(50), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    candidate_assessment: Mapped["CandidateAssessment"] = relationship("CandidateAssessment", back_populates="editor_event_batches")


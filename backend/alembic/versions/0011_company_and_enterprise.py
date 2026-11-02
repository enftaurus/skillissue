"""company_and_enterprise

Revision ID: 0011_company_and_enterprise
Revises: 0010_project_submissions
Create Date: 2026-11-02 23:58:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0011_company_and_enterprise'
down_revision: Union[str, None] = '0010_project_submissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
    -- 1. Company Tracks
    CREATE TABLE IF NOT EXISTS company_tracks (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        slug VARCHAR(100) NOT NULL UNIQUE,
        tier VARCHAR(20) NOT NULL DEFAULT 'gold',
        role_title VARCHAR(150) NOT NULL DEFAULT 'Software Development Engineer',
        description TEXT NOT NULL DEFAULT '',
        community_tips JSONB NOT NULL DEFAULT '[]'::jsonb,
        total_problems INTEGER NOT NULL DEFAULT 0,
        initial_unlocked_count INTEGER NOT NULL DEFAULT 3,
        logo_icon VARCHAR(50) NOT NULL DEFAULT 'Building2',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_company_tracks_slug ON company_tracks(slug);
    CREATE INDEX IF NOT EXISTS ix_company_tracks_tier ON company_tracks(tier);

    -- 2. Company Problems
    CREATE TABLE IF NOT EXISTS company_problems (
        id VARCHAR(36) PRIMARY KEY,
        company_track_id VARCHAR(36) NOT NULL REFERENCES company_tracks(id) ON DELETE CASCADE,
        title VARCHAR(200) NOT NULL,
        slug VARCHAR(200) NOT NULL,
        difficulty VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
        frequency_score FLOAT NOT NULL DEFAULT 100.0,
        acceptance_rate FLOAT NOT NULL DEFAULT 0.5,
        topics JSONB NOT NULL DEFAULT '[]'::jsonb,
        order_index INTEGER NOT NULL DEFAULT 1,
        is_initially_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
        description TEXT NOT NULL DEFAULT '',
        starter_code JSONB NOT NULL DEFAULT '{}'::jsonb,
        test_cases JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_company_problems_track_id ON company_problems(company_track_id);
    CREATE INDEX IF NOT EXISTS ix_company_problems_slug ON company_problems(slug);

    -- 3. User Company Progress
    CREATE TABLE IF NOT EXISTS user_company_progress (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        company_track_id VARCHAR(36) NOT NULL REFERENCES company_tracks(id) ON DELETE CASCADE,
        unlocked_count INTEGER NOT NULL DEFAULT 3,
        solved_count INTEGER NOT NULL DEFAULT 0,
        solved_problem_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
        last_practiced_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_user_company_progress UNIQUE (user_id, company_track_id)
    );
    CREATE INDEX IF NOT EXISTS ix_user_company_progress_user ON user_company_progress(user_id);

    -- 4. Retest Sessions
    CREATE TABLE IF NOT EXISTS retest_sessions (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        original_interview_id VARCHAR(36) NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
        original_evaluation_id VARCHAR(36) NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
        retest_interview_id VARCHAR(36) REFERENCES interviews(id) ON DELETE SET NULL,
        weakness_topic VARCHAR(150) NOT NULL,
        baseline_score FLOAT NOT NULL DEFAULT 0.0,
        retest_score FLOAT NOT NULL DEFAULT 0.0,
        delta_score FLOAT NOT NULL DEFAULT 0.0,
        verified_improvements JSONB NOT NULL DEFAULT '[]'::jsonb,
        status VARCHAR(30) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_retest_sessions_user_id ON retest_sessions(user_id);
    CREATE INDEX IF NOT EXISTS ix_retest_sessions_eval_id ON retest_sessions(original_evaluation_id);

    -- 5. Enterprise Assessment Pipelines
    CREATE TABLE IF NOT EXISTS assessment_pipelines (
        id VARCHAR(36) PRIMARY KEY,
        created_by_user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(200) NOT NULL,
        target_role VARCHAR(150) NOT NULL,
        job_description TEXT NOT NULL,
        rounds JSONB NOT NULL DEFAULT '[]'::jsonb,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        invite_token VARCHAR(64) NOT NULL UNIQUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_assessment_pipelines_creator ON assessment_pipelines(created_by_user_id);
    CREATE INDEX IF NOT EXISTS ix_assessment_pipelines_token ON assessment_pipelines(invite_token);

    -- 6. Candidate Assessments
    CREATE TABLE IF NOT EXISTS candidate_assessments (
        id VARCHAR(36) PRIMARY KEY,
        pipeline_id VARCHAR(36) NOT NULL REFERENCES assessment_pipelines(id) ON DELETE CASCADE,
        candidate_name VARCHAR(150) NOT NULL,
        candidate_email VARCHAR(255) NOT NULL,
        access_token VARCHAR(64) NOT NULL UNIQUE,
        status VARCHAR(30) NOT NULL DEFAULT 'invited',
        current_round_index INTEGER NOT NULL DEFAULT 0,
        round_results JSONB NOT NULL DEFAULT '{}'::jsonb,
        composite_score FLOAT NOT NULL DEFAULT 0.0,
        integrity_signals JSONB NOT NULL DEFAULT '{"window_blurs": 0, "copy_paste_count": 0, "speech_code_divergence": 0.0}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    );
    CREATE INDEX IF NOT EXISTS ix_candidate_assessments_pipeline ON candidate_assessments(pipeline_id);
    CREATE INDEX IF NOT EXISTS ix_candidate_assessments_token ON candidate_assessments(access_token);
    """)

def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS candidate_assessments;
    DROP TABLE IF EXISTS assessment_pipelines;
    DROP TABLE IF EXISTS retest_sessions;
    DROP TABLE IF EXISTS user_company_progress;
    DROP TABLE IF EXISTS company_problems;
    DROP TABLE IF EXISTS company_tracks;
    """)

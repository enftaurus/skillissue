export interface UserProfile {
  target_role: string;
  years_experience: number;
  daily_study_minutes: number;
  bio?: string;
}

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  profile?: UserProfile;
}

export interface ProviderConfig {
  id: string;
  provider_name: string;
  aws_region: string;
  aws_access_key_masked: string;
  preferred_model: string;
  is_valid: boolean;
  last_tested_at?: string;
  total_tokens_used: number;
  estimated_cost_usd: number;
}

export interface ModelMetadata {
  model_id: string;
  provider: string;
  display_name: string;
  role: string;
  description: string;
  supported_regions: string[];
  input_price_per_1m: number;
  output_price_per_1m: number;
  context_window: number;
  max_output_tokens: number;
  recommended_for: string;
  is_default: boolean;
}

export interface Resume {
  id: string;
  file_name: string;
  extracted_skills: string[];
  projects_context: Array<{ name: string; tech: string; summary: string }>;
  created_at: string;
}

export interface JobDescription {
  id: string;
  title: string;
  company: string;
  raw_text: string;
  extracted_role: string;
  extracted_skills: string[];
  extracted_requirements: string[];
  created_at: string;
}

export interface InterviewMessage {
  id: string;
  interview_id: string;
  role: 'assistant' | 'user' | 'system';
  content: string;
  question_index: number;
  is_follow_up: boolean;
  created_at: string;
}

export interface Interview {
  id: string;
  mode: 'domain' | 'jd';
  category: 'technical' | 'behavioral' | 'dsa' | 'managerial';
  title: string;
  target_role: string;
  difficulty: string;
  status: 'in_progress' | 'completed' | 'cancelled';
  domain_skills: string[];
  jd_id?: string;
  resume_id?: string;
  target_duration_minutes: number;
  created_at: string;
  completed_at?: string;
  messages?: InterviewMessage[];
}

export interface RubricDimension {
  id: string;
  name: string;
  description: string;
  max_score: number;
  scoring_criteria: Record<number, string>;
}

export interface DimensionComparison {
  dimension_id: string;
  dimension_name: string;
  self_score?: number;
  ai_score: number;
  delta?: number;
  evidence_quote: string;
  explanation: string;
}

export interface EvaluationComparison {
  interview_id: string;
  overall_ai_score: number;
  dimensions: DimensionComparison[];
  self_reflection: string;
  strengths: string[];
  weaknesses: string[];
  missing_concepts: string[];
}

export interface Evaluation {
  id: string;
  interview_id: string;
  overall_score: number;
  rubric_dimension_scores: Record<string, {
    score: number;
    max_score: number;
    explanation: string;
    evidence_quote: string;
  }>;
  strengths: string[];
  weaknesses: string[];
  missing_concepts: string[];
  evidence_excerpts: Array<{ quote: string; critique: string }>;
  suggested_corrections: string[];
  uncertainty_notes: string[];
  tokens_used: number;
  model_identifier: string;
  created_at: string;
}

export interface PlanTask {
  id: string;
  plan_id: string;
  day_number: number;
  title: string;
  description: string;
  task_type: 'concept' | 'practice' | 'coding' | 'reassessment';
  estimated_minutes: number;
  external_resources: Array<{ title: string; url: string; type: string }>;
  is_completed: boolean;
  completed_at?: string;
}

export interface Plan {
  id: string;
  evaluation_id?: string;
  title: string;
  target_role: string;
  target_skills: string[];
  status: 'active' | 'completed' | 'archived';
  total_days: number;
  current_day: number;
  daily_study_minutes: number;
  tasks: PlanTask[];
  created_at: string;
  updated_at: string;
}

export interface CodingProblem {
  id: string;
  title: string;
  difficulty: 'easy' | 'medium' | 'hard';
  description: string;
  input_format: string;
  output_format: string;
  constraints: string[];
  starter_code: Record<string, string>;
  sample_test_cases: Array<{ stdin: string; expected_stdout: string }>;
}

export interface TestCaseResult {
  test_index: number;
  passed: boolean;
  stdin: string;
  expected_stdout: string;
  actual_stdout: string;
  stderr: string;
  execution_time_ms: number;
  is_hidden: boolean;
}

export interface CodeExecutionResult {
  status: 'passed' | 'failed' | 'timeout' | 'compile_error' | 'runtime_error';
  stdout: string;
  stderr: string;
  execution_time_ms: number;
  total_passed: number;
  total_tests: number;
  test_results: TestCaseResult[];
}

export interface AnalyticsDashboard {
  total_interviews: number;
  completed_interviews: number;
  average_overall_score: number;
  plan_tasks_completed: number;
  plan_tasks_total: number;
  planly_completion_rate: number;
  score_history: Array<{
    interview_id: string;
    title: string;
    category: string;
    mode: string;
    overall_score: number;
    completed_at: string;
  }>;
  dimension_trends: Array<{
    dimension_id: string;
    dimension_name: string;
    scores: number[];
    latest_score: number;
    average_score: number;
  }>;
  recurring_strengths: string[];
  recurring_weaknesses: string[];
  reassessments: Array<{
    baseline_interview_id: string;
    baseline_title: string;
    baseline_date: string;
    baseline_score: number;
    reassessment_interview_id: string;
    reassessment_title: string;
    reassessment_date: string;
    reassessment_score: number;
    score_delta: number;
    category: string;
    is_comparable: boolean;
    improved_dimensions: string[];
    stable_dimensions: string[];
    declined_dimensions: string[];
  }>;
}

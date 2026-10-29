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
  onboarding_completed?: boolean;
  is_provider_connected?: boolean;
  created_at: string;
  profile?: UserProfile;
}

export interface ProviderConfig {
  id: string;
  provider_name: string;
  aws_region?: string;
  aws_access_key_masked: string;
  azure_endpoint?: string;
  azure_api_version?: string;
  azure_deployment_name?: string;
  preferred_model: string;
  default_model?: string;
  interviewer_model?: string;
  evaluation_model?: string;
  coding_model?: string;
  planning_model?: string;
  fallback_enabled?: boolean;
  fallback_provider?: string;
  fallback_model?: string;
  temperature?: number;
  max_tokens?: number;
  is_valid: boolean;
  total_tokens_used: number;
  estimated_cost_usd: number;
  monthly_token_budget?: number;
  monthly_tokens_used?: number;
  monthly_cost_cents_budget?: number;
  monthly_cost_cents_used?: number;
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
  supports_structured_output?: boolean;
  supports_tool_calling?: boolean;
  supports_streaming?: boolean;
  supports_vision?: boolean;
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

export interface QuestionTurn {
  question_index: number;
  interviewer_question: string;
  candidate_answer: string;
  is_follow_up: boolean;
  assistant_message_id?: string;
  user_message_id?: string;
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
  coding_problem_id?: string;
  hint_level_used?: number;
  target_duration_minutes: number;
  created_at: string;
  completed_at?: string;
  messages?: InterviewMessage[];
  grouped_transcript?: QuestionTurn[];
}

export interface HintResponse {
  level: number;
  hint: string;
  penalty_pct: number;
  total_hint_level_used: number;
  message_id: string;
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

export interface QuestionSelfEvaluation {
  question_index: number;
  interviewer_question?: string;
  candidate_answer?: string;
  score: number;
  strengths?: string;
  missed_points?: string;
  confidence?: string;
}

export interface SelfEvaluation {
  id: string;
  interview_id: string;
  dimension_scores: Record<string, number>;
  reflection: string;
  question_evaluations?: QuestionSelfEvaluation[];
  created_at: string;
}

export interface QuestionComparison {
  question_index: number;
  interviewer_question: string;
  candidate_answer: string;
  self_score?: number;
  self_strengths?: string;
  self_missed_points?: string;
  self_confidence?: string;
  ai_verbatim_quote?: string;
  ai_critique?: string;
  ai_guide?: string;
  score_gap?: number;
  targeted_resource?: string;
}

export interface WeaknessAnalysisItem {
  id: string;
  topic: string;
  subtopic?: string;
  evidence: string;
  gap_explanation: string;
  learning_objective: string;
  suggested_exercise?: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface EvaluationComparison {
  interview_id: string;
  overall_ai_score: number;
  dimensions: DimensionComparison[];
  question_comparisons?: QuestionComparison[];
  self_reflection: string;
  strengths: string[];
  weaknesses: string[];
  missing_concepts: string[];
  weakness_analysis?: WeaknessAnalysisItem[];
}

export interface QuestionFeedback {
  question_index: number;
  interviewer_question: string;
  candidate_answer: string;
  verbatim_quote: string;
  critique: string;
  strong_answer_guide: string;
  targeted_resource?: string;
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
  weakness_analysis?: WeaknessAnalysisItem[];
  missing_concepts: string[];
  evidence_excerpts: Array<{ quote: string; critique: string }>;
  question_feedback?: QuestionFeedback[];
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
  topic?: string;
  goal?: string;
  target_role: string;
  target_skills: string[];
  schedule_days?: string[];
  current_level?: string;
  status: 'active' | 'completed' | 'archived';
  total_days: number;
  current_day: number;
  daily_study_minutes: number;
  start_date?: string;
  target_date?: string;
  tasks: PlanTask[];
  created_at: string;
  updated_at: string;
}

export interface CustomPlanRequest {
  topic: string;
  goal?: 'fundamentals' | 'interview_prep' | 'mastery';
  daily_study_minutes?: number;
  schedule_days?: string[];
  current_level?: 'beginner' | 'intermediate' | 'advanced';
  start_date?: string;
  deadline?: string;
}

export interface LearningBacklogItem {
  id: string;
  user_id: string;
  topic: string;
  subtopic?: string;
  source: string;
  source_id?: string;
  reason: string;
  learning_objective?: string;
  suggested_exercise?: string;
  priority: 'low' | 'medium' | 'high';
  status: 'queued' | 'planned' | 'in_progress' | 'completed' | 'dismissed';
  notes?: string;
  planned_plan_id?: string;
  created_at: string;
  updated_at: string;
  is_existing?: boolean;
}

export interface QueueWeaknessRequest {
  interview_id?: string;
  weakness_id?: string;
  topic: string;
  subtopic?: string;
  evidence?: string;
  gap_explanation?: string;
  learning_objective?: string;
  suggested_exercise?: string;
  priority?: 'low' | 'medium' | 'high';
  notes?: string;
}

export interface SuggestedBacklogItem {
  id: string;
  topic: string;
  subtopic?: string;
  reason: string;
  source: string;
  source_id?: string;
  priority: string;
  status: string;
  suggested_reason: string;
}

export interface CodingProblem {
  id: string;
  title: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category?: string;
  description: string;
  input_format: string;
  output_format: string;
  constraints: string[];
  starter_code: Record<string, string>;
  sample_test_cases: Array<{ stdin: string; expected_stdout: string }>;
  ai_coaching_supported?: boolean;
}

export interface DsaCoachRequest {
  hint_level: number;
  user_code?: string;
  language?: string;
  user_message?: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface DsaCoachResponse {
  hint_level: number;
  hint_text: string;
  guiding_question: string;
  suggested_focus?: string;
  tokens_used?: number;
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
  skills?: UserSkill[];
}

export interface UserSkill {
  id: string;
  topic: string;
  score: number;
  confidence: number;
  last_seen: string;
  evidence_refs: Array<{ type?: string; id?: string; score?: number; [key: string]: any }>;
}

export interface TaskShiftPreview {
  task_id: string;
  title: string;
  current_day: number;
  new_day: number;
  task_type: string;
}

export interface PlanAdaptPreview {
  plan_id: string;
  days_behind: number;
  current_total_days: number;
  new_total_days: number;
  shifted_tasks: TaskShiftPreview[];
}

export interface CodingLimits {
  memory_limit_mb: number;
  timeout_seconds: number;
  output_limit_bytes: number;
  runtime: string;
}

export interface CodingSubmission {
  id: string;
  problem_title: string;
  language: string;
  status: string;
  execution_time_ms: number;
  memory_kb?: number;
  tests_passed: number;
  tests_total: number;
  created_at: string;
}


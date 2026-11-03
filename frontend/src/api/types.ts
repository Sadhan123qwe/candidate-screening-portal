// These mirror the response models in backend/app/schemas.py.

export const APPLICATION_STATUSES = ["Applied", "Shortlisted", "Rejected"] as const;
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApplicationCounts {
  Applied: number;
  Shortlisted: number;
  Rejected: number;
}

export interface Job {
  id: number;
  external_ref: string | null;
  title: string;
  description: string;
  min_experience_years: number;
  required_skills: string[];
  preferred_skills: string[];
  version: number;
  created_at: string;
  updated_at: string;
  application_counts: ApplicationCounts;
}

export interface JobInput {
  title: string;
  description: string;
  min_experience_years: number;
  required_skills: string[];
  preferred_skills: string[];
}

export interface Prediction {
  label: "Potential Match" | "Needs Review";
  probability: number;
  model_version: string;
  computed_at: string;
}

export interface Application {
  id: number;
  candidate_id: number;
  candidate_name: string;
  job_id: number;
  job_title: string;
  status: ApplicationStatus;
  version: number;
  created_at: string;
  updated_at: string;
  prediction: Prediction | null;
  prediction_message: string | null;
}

export interface FeatureContribution {
  feature: string;
  value: number;
  contribution: number;
}

export interface ApplicationDetail extends Application {
  candidate_email: string;
  top_features: FeatureContribution[];
}

export interface ApplicationPage {
  items: Application[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatusHistoryEntry {
  id: number;
  old_status: ApplicationStatus;
  new_status: ApplicationStatus;
  changed_by_user_id: number;
  changed_by_name: string;
  changed_at: string;
}

export interface Candidate {
  id: number;
  external_ref: string | null;
  name: string;
  email: string;
  experience_years: number;
  profile_summary: string;
  skills: string[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CandidateDetail extends Candidate {
  applications: Application[];
}

export interface CandidateInput {
  name: string;
  email: string;
  experience_years: number;
  profile_summary: string;
  skills: string[];
}

export interface ClassificationResult {
  precision: number;
  recall: number;
  f1: number;
  confusion_matrix: { tn: number; fp: number; fn: number; tp: number };
}

export interface CvResult {
  params: Record<string, number>;
  mean_f1: number;
  std_f1: number;
}

export interface ModelMetrics {
  model_name: string;
  model_version: string;
  trained_at: string;
  decision_threshold: number;
  dataset: {
    train_applications: number;
    test_applications: number;
    train_candidates: number;
    test_candidates: number;
    train_positive_rate: number;
    test_positive_rate: number;
    train_match_rate_with_all_required: number;
    train_match_rate_without_all_required: number;
  };
  baseline: { rule: string; threshold: number; reason: string; train_f1: number };
  cross_validation: {
    method: string;
    scoring: string;
    best_by_model: Record<string, number>;
    results: Record<string, CvResult[]>;
  };
  chosen_model: { name: string; params: Record<string, number>; mean_cv_f1: number };
  test: { baseline: ClassificationResult; model: ClassificationResult };
}

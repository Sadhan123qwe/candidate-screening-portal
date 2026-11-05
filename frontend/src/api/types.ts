// These mirror the response models in backend/app/schemas.py.

export const APPLICATION_STATUSES = ["Applied", "Shortlisted", "Rejected"] as const;
export type ApplicationStatus = (typeof APPLICATION_STATUSES)[number];

export const PREDICTION_LABELS = ["Potential Match", "Needs Review"] as const;

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

export interface PortalStats {
  jobs: number;
  candidates: number;
  applications: number;
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

export interface JobSummary {
  job_id: number;
  applied: number;
  shortlisted: number;
  rejected: number;
  potential_match: number | null;
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
  candidate_email: string;
  candidate_experience_years: number;
  job_id: number;
  job_title: string;
  required_matched: number;
  required_total: number;
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
  top_features: FeatureContribution[];
  candidate_profile_summary: string;
  job_min_experience_years: number;
  experience_gap: number;
  required_skills_matched: string[];
  required_skills_missing: string[];
  preferred_skills_matched: string[];
  preferred_skills_missing: string[];
  other_candidate_skills: string[];
  imported_from_dataset: boolean;
}

export interface ApplicationSummary {
  total: number;
  applied: number;
  shortlisted: number;
  rejected: number;
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
  application_count: number;
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

export interface MeanStd {
  mean: number;
  std: number;
}

export interface PrecisionRecallPoint {
  threshold: number | null;
  precision: number;
  recall: number;
}

export interface ModelMetrics {
  model_name: string;
  model_version: string;
  trained_at: string;
  decision_threshold: number;
  threshold_selection: {
    method: string;
    default_threshold: number;
    minimum_gain: number;
    best_threshold: number;
    best_mean_cv_f1: number;
    default_mean_cv_f1: number;
    gain: number;
    adopted: boolean;
    selected_threshold: number;
    reason: string;
  };
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
    best_model_summary: Record<string, { f1: MeanStd; precision: MeanStd; recall: MeanStd }>;
  };
  feature_importance: {
    method: string;
    scoring: string;
    features: ({ feature: string } & MeanStd)[];
  };
  chosen_model: { name: string; params: Record<string, number>; mean_cv_f1: number };
  test: { baseline: ClassificationResult; model: ClassificationResult };
  precision_recall_curve: { average_precision: number; points: PrecisionRecallPoint[] };
}

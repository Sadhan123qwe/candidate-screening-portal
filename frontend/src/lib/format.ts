// en-GB gives the day-first dates used throughout the design, such as "2 Nov 2026".
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatYears(value: number): string {
  return `${value} yr`;
}

/** Signed for a gap, so a shortfall can't be mistaken for extra experience. */
export function formatSignedYears(value: number): string {
  if (value === 0) return "0 yr";
  return `${value > 0 ? "+" : "\u2212"}${Math.abs(value)} yr`;
}

/** A contribution to the probability, in percentage points. */
export function formatPoints(contribution: number): string {
  const points = Math.round(contribution * 100);
  if (points === 0) return "0 pts";
  return `${points > 0 ? "+" : "\u2212"}${Math.abs(points)} pts`;
}

const FEATURE_LABELS: Record<string, string> = {
  required_overlap_ratio: "Required skills matched",
  required_missing_count: "Required skills missing",
  has_all_required: "Has every required skill",
  preferred_overlap_ratio: "Preferred skills matched",
  skill_jaccard: "Overlap with job skills",
  extra_skill_count: "Other skills",
  candidate_skill_count: "Candidate's skill count",
  experience_years: "Candidate experience",
  min_experience_years: "Job minimum experience",
  experience_gap: "Experience gap",
  meets_experience: "Meets the job minimum",
};

/** Turns "required_overlap_ratio" into "Required skills matched". */
export function formatFeatureName(name: string): string {
  const fallback = name.replace(/_/g, " ");
  return FEATURE_LABELS[name] ?? fallback.charAt(0).toUpperCase() + fallback.slice(1);
}

interface MatchCounts {
  required_matched: number;
  required_total: number;
  preferred_matched: number;
  preferred_total: number;
}

/** The feature's value in the terms a recruiter would use: "3 of 3", "Yes", "-0.75 yr". */
export function formatFeatureValue(name: string, value: number, counts: MatchCounts): string {
  switch (name) {
    case "required_overlap_ratio":
      return `${counts.required_matched} of ${counts.required_total}`;
    case "preferred_overlap_ratio":
      return `${counts.preferred_matched} of ${counts.preferred_total}`;
    case "has_all_required":
    case "meets_experience":
      return value ? "Yes" : "No";
    case "experience_gap":
      return formatSignedYears(value);
    case "experience_years":
    case "min_experience_years":
      return formatYears(value);
    case "skill_jaccard":
      return value.toFixed(2);
    default:
      return String(value);
  }
}

/** "Python, SQL ,python" becomes ["python", "sql"]: the same cleaning the server applies. */
export function parseSkills(text: string): string[] {
  const skills = text
    .split(",")
    .map((skill) => skill.trim().toLowerCase())
    .filter(Boolean);
  return [...new Set(skills)];
}

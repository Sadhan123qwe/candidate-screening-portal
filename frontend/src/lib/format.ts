export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatYears(value: number): string {
  return `${value} ${value === 1 ? "year" : "years"}`;
}

/** Turns "required_overlap_ratio" into "Required overlap ratio". */
export function formatFeatureName(name: string): string {
  const words = name.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** "Python, SQL ,python" becomes ["python", "sql"]: the same cleaning the server applies. */
export function parseSkills(text: string): string[] {
  const skills = text
    .split(",")
    .map((skill) => skill.trim().toLowerCase())
    .filter(Boolean);
  return [...new Set(skills)];
}

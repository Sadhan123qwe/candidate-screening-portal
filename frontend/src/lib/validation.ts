// Client-side checks give instant feedback. They mirror backend/app/schemas.py, but the
// server stays the authority, and its errors are always shown as well.

const SKILL_PATTERN = /^[a-z0-9.+#-]+$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_NAME_LENGTH = 120;
const MAX_EXPERIENCE_YEARS = 50;

export type FieldErrors = Record<string, string>;

export function validateName(value: string, label: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return `${label} is required.`;
  if (trimmed.length > MAX_NAME_LENGTH) return `${label} must be ${MAX_NAME_LENGTH} characters or fewer.`;
  return undefined;
}

export function validateEmail(value: string): string | undefined {
  if (!value.trim()) return "Email is required.";
  if (!EMAIL_PATTERN.test(value.trim())) return "Enter a valid email address.";
  return undefined;
}

export function validateExperience(value: string): string | undefined {
  if (value.trim() === "") return "Experience is required.";
  const years = Number(value);
  if (Number.isNaN(years) || years < 0 || years > MAX_EXPERIENCE_YEARS) {
    return `Enter a number from 0 to ${MAX_EXPERIENCE_YEARS}.`;
  }
  return undefined;
}

export function validateSkills(skills: string[], { required }: { required: boolean }): string | undefined {
  if (required && skills.length === 0) return "Enter at least one skill.";
  const invalid = skills.find((skill) => !SKILL_PATTERN.test(skill));
  if (invalid) return `"${invalid}" isn't valid. Use only letters, numbers and . + # -`;
  return undefined;
}

export function withoutEmptyErrors(errors: Record<string, string | undefined>): FieldErrors {
  const result: FieldErrors = {};
  for (const [field, message] of Object.entries(errors)) {
    if (message) result[field] = message;
  }
  return result;
}

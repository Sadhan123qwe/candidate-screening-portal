import { useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import type { Job, JobInput } from "../api/types";
import { parseSkills } from "../lib/format";
import { validateExperience, validateName, validateSkills, withoutEmptyErrors, type FieldErrors } from "../lib/validation";
import { ErrorNotice, Field } from "./FormParts";

interface JobFormProps {
  /** The job being edited. Leave out to create a new one. */
  job?: Job;
  submitLabel: string;
  isSubmitting: boolean;
  serverError: Error | null;
  onSubmit: (input: JobInput) => void;
  onCancel: () => void;
}

export function JobForm({ job, submitLabel, isSubmitting, serverError, onSubmit, onCancel }: JobFormProps) {
  const [title, setTitle] = useState(job?.title ?? "");
  const [description, setDescription] = useState(job?.description ?? "");
  const [minExperience, setMinExperience] = useState(String(job?.min_experience_years ?? 0));
  const [required, setRequired] = useState(job?.required_skills.join(", ") ?? "");
  const [preferred, setPreferred] = useState(job?.preferred_skills.join(", ") ?? "");
  const [clientErrors, setClientErrors] = useState<FieldErrors>({});

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const requiredSkills = parseSkills(required);
    const preferredSkills = parseSkills(preferred);
    const both = requiredSkills.filter((skill) => preferredSkills.includes(skill));

    const errors = withoutEmptyErrors({
      title: validateName(title, "Title"),
      min_experience_years: validateExperience(minExperience),
      required_skills: validateSkills(requiredSkills, { required: true }),
      preferred_skills:
        validateSkills(preferredSkills, { required: false }) ??
        (both.length > 0 ? `Can't be both required and preferred: ${both.join(", ")}` : undefined),
    });
    setClientErrors(errors);
    if (Object.keys(errors).length > 0) return;

    onSubmit({
      title: title.trim(),
      description: description.trim(),
      min_experience_years: Number(minExperience),
      required_skills: requiredSkills,
      preferred_skills: preferredSkills,
    });
  }

  const serverFieldErrors = serverError instanceof ApiError ? serverError.fieldErrors : {};
  const errorFor = (field: string) => clientErrors[field] ?? serverFieldErrors[field];

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <Field id="job-title" label="Title" error={errorFor("title")}>
        <input id="job-title" className="input" value={title} onChange={(event) => setTitle(event.target.value)} />
      </Field>
      <Field id="job-description" label="Description" error={errorFor("description")}>
        <textarea id="job-description" rows={3} className="input" value={description} onChange={(event) => setDescription(event.target.value)} />
      </Field>
      <Field id="job-min-experience" label="Minimum experience (years)" error={errorFor("min_experience_years")}>
        <input id="job-min-experience" type="number" step="0.25" min="0" max="50" className="input" value={minExperience} onChange={(event) => setMinExperience(event.target.value)} />
      </Field>
      <Field id="job-required" label="Required skills" hint="Separate with commas" error={errorFor("required_skills")}>
        <input id="job-required" className="input" placeholder="python, sql" value={required} onChange={(event) => setRequired(event.target.value)} />
      </Field>
      <Field id="job-preferred" label="Preferred skills" hint="Optional. Separate with commas" error={errorFor("preferred_skills")}>
        <input id="job-preferred" className="input" placeholder="docker, git" value={preferred} onChange={(event) => setPreferred(event.target.value)} />
      </Field>
      <ErrorNotice message={serverError?.message} />
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}

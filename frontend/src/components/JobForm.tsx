import { forwardRef, useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import type { Job, JobInput } from "../api/types";
import { validateExperience, validateName, validateSkills, withoutEmptyErrors, type FieldErrors } from "../lib/validation";
import { Button } from "./ui/Button";
import { Input, Textarea } from "./ui/Controls";
import { ErrorNotice } from "./ui/Notice";
import { SkillInput } from "./ui/SkillInput";

interface JobFormProps {
  /** The job being edited. Leave out to create a new one. */
  job?: Job;
  submitLabel: string;
  isSubmitting: boolean;
  serverError: Error | null;
  onSubmit: (input: JobInput) => void;
  onCancel: () => void;
}

function overlapError(skills: string[]): string | undefined {
  if (skills.length === 0) return undefined;
  if (skills.length === 1) return `${skills[0]} is already a required skill. Remove it from one list.`;
  return `${skills.join(", ")} are already required skills. Remove them from one list.`;
}

/** The ref is the title field, so the page can send people straight to the form. */
export const JobForm = forwardRef<HTMLInputElement, JobFormProps>(function JobForm(
  { job, submitLabel, isSubmitting, serverError, onSubmit, onCancel },
  titleRef,
) {
  const [title, setTitle] = useState(job?.title ?? "");
  const [description, setDescription] = useState(job?.description ?? "");
  const [minExperience, setMinExperience] = useState(String(job?.min_experience_years ?? 0));
  const [required, setRequired] = useState(job?.required_skills ?? []);
  const [preferred, setPreferred] = useState(job?.preferred_skills ?? []);
  const [clientErrors, setClientErrors] = useState<FieldErrors>({});

  // Checked as the lists change, so the conflict shows the moment it's created.
  const overlap = overlapError(preferred.filter((skill) => required.includes(skill)));

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const errors = withoutEmptyErrors({
      title: validateName(title, "Title"),
      min_experience_years: validateExperience(minExperience),
      required_skills: validateSkills(required, { required: true }),
      preferred_skills: validateSkills(preferred, { required: false }) ?? overlap,
    });
    setClientErrors(errors);
    if (Object.keys(errors).length > 0) return;

    onSubmit({
      title: title.trim(),
      description: description.trim(),
      min_experience_years: Number(minExperience),
      required_skills: required,
      preferred_skills: preferred,
    });
  }

  const serverFieldErrors = serverError instanceof ApiError ? serverError.fieldErrors : {};
  const errorFor = (field: string) => clientErrors[field] ?? serverFieldErrors[field];

  return (
    <form onSubmit={handleSubmit} noValidate className="form-stack">
      <Input ref={titleRef} id="job-title" label="Title" value={title} error={errorFor("title")} onChange={(event) => setTitle(event.target.value)} />
      <Textarea
        id="job-description"
        label="Description"
        placeholder="What the intern will work on"
        value={description}
        error={errorFor("description")}
        onChange={(event) => setDescription(event.target.value)}
      />
      <SkillInput id="job-required" label="Required skills" value={required} error={errorFor("required_skills")} onChange={setRequired} />
      <SkillInput
        id="job-preferred"
        label="Preferred skills"
        value={preferred}
        error={overlap ?? errorFor("preferred_skills")}
        onChange={setPreferred}
      />
      <Input
        id="job-min-experience"
        label="Minimum experience (years)"
        type="number"
        step="0.25"
        min="0"
        max="50"
        className="num"
        value={minExperience}
        error={errorFor("min_experience_years")}
        onChange={(event) => setMinExperience(event.target.value)}
      />
      <ErrorNotice message={serverError?.message} />
      <div className="form-actions">
        <Button onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="primary" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : submitLabel}
        </Button>
      </div>
    </form>
  );
});

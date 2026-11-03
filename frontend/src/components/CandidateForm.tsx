import { useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import type { Candidate, CandidateInput } from "../api/types";
import { parseSkills } from "../lib/format";
import { validateEmail, validateExperience, validateName, validateSkills, withoutEmptyErrors, type FieldErrors } from "../lib/validation";
import { ErrorNotice, Field } from "./FormParts";

interface CandidateFormProps {
  /** The candidate being edited. Leave out to create a new one. */
  candidate?: Candidate;
  submitLabel: string;
  isSubmitting: boolean;
  serverError: Error | null;
  onSubmit: (input: CandidateInput) => void;
  onCancel: () => void;
}

export function CandidateForm({ candidate, submitLabel, isSubmitting, serverError, onSubmit, onCancel }: CandidateFormProps) {
  const [name, setName] = useState(candidate?.name ?? "");
  const [email, setEmail] = useState(candidate?.email ?? "");
  const [experience, setExperience] = useState(String(candidate?.experience_years ?? ""));
  const [skills, setSkills] = useState(candidate?.skills.join(", ") ?? "");
  const [summary, setSummary] = useState(candidate?.profile_summary ?? "");
  const [clientErrors, setClientErrors] = useState<FieldErrors>({});

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const parsedSkills = parseSkills(skills);

    const errors = withoutEmptyErrors({
      name: validateName(name, "Name"),
      email: validateEmail(email),
      experience_years: validateExperience(experience),
      skills: validateSkills(parsedSkills, { required: true }),
    });
    setClientErrors(errors);
    if (Object.keys(errors).length > 0) return;

    onSubmit({
      name: name.trim(),
      email: email.trim(),
      experience_years: Number(experience),
      profile_summary: summary.trim(),
      skills: parsedSkills,
    });
  }

  const serverFieldErrors = serverError instanceof ApiError ? serverError.fieldErrors : {};
  const errorFor = (field: string) => clientErrors[field] ?? serverFieldErrors[field];

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <Field id="candidate-name" label="Name" error={errorFor("name")}>
        <input id="candidate-name" className="input" value={name} onChange={(event) => setName(event.target.value)} />
      </Field>
      <Field id="candidate-email" label="Email" error={errorFor("email")}>
        <input id="candidate-email" type="email" className="input" value={email} onChange={(event) => setEmail(event.target.value)} />
      </Field>
      <Field id="candidate-experience" label="Experience (years)" error={errorFor("experience_years")}>
        <input id="candidate-experience" type="number" step="0.25" min="0" max="50" className="input" value={experience} onChange={(event) => setExperience(event.target.value)} />
      </Field>
      <Field id="candidate-skills" label="Skills" hint="Separate with commas" error={errorFor("skills")}>
        <input id="candidate-skills" className="input" placeholder="python, sql" value={skills} onChange={(event) => setSkills(event.target.value)} />
      </Field>
      <Field id="candidate-summary" label="Profile summary" error={errorFor("profile_summary")}>
        <textarea id="candidate-summary" rows={3} className="input" value={summary} onChange={(event) => setSummary(event.target.value)} />
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

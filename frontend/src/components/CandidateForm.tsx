import { forwardRef, useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import type { Candidate, CandidateInput } from "../api/types";
import { validateEmail, validateExperience, validateName, validateSkills, withoutEmptyErrors, type FieldErrors } from "../lib/validation";
import { Button } from "./ui/Button";
import { Input, Textarea } from "./ui/Controls";
import { ErrorNotice } from "./ui/Notice";
import { SkillInput } from "./ui/SkillInput";

interface CandidateFormProps {
  /** The candidate being edited. Leave out to create a new one. */
  candidate?: Candidate;
  submitLabel: string;
  isSubmitting: boolean;
  serverError: Error | null;
  onSubmit: (input: CandidateInput) => void;
  onCancel: () => void;
}

/** The ref is the name field, so the page can send people straight to the form. */
export const CandidateForm = forwardRef<HTMLInputElement, CandidateFormProps>(function CandidateForm(
  { candidate, submitLabel, isSubmitting, serverError, onSubmit, onCancel },
  nameRef,
) {
  const [name, setName] = useState(candidate?.name ?? "");
  const [email, setEmail] = useState(candidate?.email ?? "");
  const [experience, setExperience] = useState(String(candidate?.experience_years ?? ""));
  const [skills, setSkills] = useState(candidate?.skills ?? []);
  const [summary, setSummary] = useState(candidate?.profile_summary ?? "");
  const [clientErrors, setClientErrors] = useState<FieldErrors>({});

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const errors = withoutEmptyErrors({
      name: validateName(name, "Full name"),
      email: validateEmail(email),
      experience_years: validateExperience(experience),
      skills: validateSkills(skills, { required: true }),
    });
    setClientErrors(errors);
    if (Object.keys(errors).length > 0) return;

    onSubmit({
      name: name.trim(),
      email: email.trim(),
      experience_years: Number(experience),
      profile_summary: summary.trim(),
      skills,
    });
  }

  const serverFieldErrors = serverError instanceof ApiError ? serverError.fieldErrors : {};
  const errorFor = (field: string) => clientErrors[field] ?? serverFieldErrors[field];

  return (
    <form onSubmit={handleSubmit} noValidate className="form-stack">
      <Input ref={nameRef} id="candidate-name" label="Full name" value={name} error={errorFor("name")} onChange={(event) => setName(event.target.value)} />
      <Input id="candidate-email" label="Email" type="email" value={email} error={errorFor("email")} onChange={(event) => setEmail(event.target.value)} />
      <Input
        id="candidate-experience"
        label="Experience (years)"
        type="number"
        step="0.25"
        min="0"
        max="50"
        className="num"
        value={experience}
        error={errorFor("experience_years")}
        onChange={(event) => setExperience(event.target.value)}
      />
      <SkillInput id="candidate-skills" label="Skills" value={skills} error={errorFor("skills")} onChange={setSkills} />
      <Textarea id="candidate-summary" label="Profile summary" value={summary} error={errorFor("profile_summary")} onChange={(event) => setSummary(event.target.value)} />
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

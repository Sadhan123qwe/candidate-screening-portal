import { useState, type KeyboardEvent } from "react";
import { errorAttributes, Field } from "./Controls";
import { SkillTag } from "./SkillTag";

/** "Python, SQL" becomes ["python", "sql"]: the same cleaning the server applies. */
function cleanSkills(text: string): string[] {
  return text
    .split(",")
    .map((skill) => skill.trim().toLowerCase())
    .filter(Boolean);
}

interface SkillInputProps {
  id: string;
  label: string;
  value: string[];
  onChange: (skills: string[]) => void;
  error?: string;
  placeholder?: string;
}

/** Skills as removable tags. Enter, a comma or leaving the field turns the typed text into a tag. */
export function SkillInput({ id, label, value, onChange, error, placeholder = "Add skill" }: SkillInputProps) {
  const [draft, setDraft] = useState("");

  function commitDraft() {
    const added = cleanSkills(draft);
    if (added.length > 0) onChange([...new Set([...value, ...added])]);
    setDraft("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault(); // Enter here adds a skill, rather than submitting the form early.
      commitDraft();
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  return (
    <Field id={id} label={label} error={error}>
      <div className={`skill-input ${error ? "control-error" : ""}`}>
        {value.map((skill) => (
          <button
            key={skill}
            type="button"
            className="skill-remove"
            aria-label={`Remove ${skill}`}
            title={`Remove ${skill}`}
            onClick={() => onChange(value.filter((item) => item !== skill))}
          >
            <SkillTag skill={skill} />
          </button>
        ))}
        <input
          id={id}
          value={draft}
          placeholder={placeholder}
          autoComplete="off"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commitDraft}
          {...errorAttributes(id, error)}
        />
      </div>
    </Field>
  );
}

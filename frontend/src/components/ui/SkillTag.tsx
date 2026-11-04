const VARIANT = { neutral: "", hit: "skill-tag-hit", miss: "skill-tag-miss" };

interface SkillTagProps {
  skill: string;
  variant?: keyof typeof VARIANT;
}

export function SkillTag({ skill, variant = "neutral" }: SkillTagProps) {
  return <span className={`skill-tag ${VARIANT[variant]}`}>{skill}</span>;
}

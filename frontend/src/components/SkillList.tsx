export function SkillList({ skills, muted }: { skills: string[]; muted?: boolean }) {
  if (skills.length === 0) return <span className="text-sm text-gray-500">None</span>;
  const colors = muted ? "bg-gray-50 text-gray-600 ring-gray-200" : "bg-accent-50 text-accent-800 ring-accent-200";
  return (
    <ul className="flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <li key={skill} className={`rounded px-2 py-0.5 text-xs ring-1 ring-inset ${colors}`}>
          {skill}
        </li>
      ))}
    </ul>
  );
}

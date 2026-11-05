import { useCallback, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useCandidates, useCreateCandidate } from "../api/candidates";
import { CandidateForm } from "../components/CandidateForm";
import { QueryBoundary } from "../components/QueryBoundary";
import { SearchBox } from "../components/SearchBox";
import { Button } from "../components/ui/Button";
import { GlassCard } from "../components/ui/GlassCard";
import { PageHeader } from "../components/ui/PageHeader";
import { SkillTag } from "../components/ui/SkillTag";
import { formatYears } from "../lib/format";

const VISIBLE_SKILLS = 4;

export function CandidatesPage() {
  const [params, setParams] = useSearchParams();
  const search = params.get("search") ?? "";
  const candidates = useCandidates(search);
  const createCandidate = useCreateCandidate();
  const nameRef = useRef<HTMLInputElement>(null);
  // A new key remounts the form, which is the simplest way to clear every field.
  const [formKey, setFormKey] = useState(0);

  const handleSearch = useCallback(
    (value: string) => setParams(value ? { search: value } : {}),
    [setParams],
  );

  function resetForm() {
    setFormKey((key) => key + 1);
    createCandidate.reset();
  }

  const note = "Names and emails are shown here but never used by the model.";
  // The total only makes sense without a search narrowing the list.
  const subtitle = !search && candidates.data ? `${candidates.data.length} candidates. ${note}` : note;

  return (
    <div>
      <PageHeader
        title="Candidates"
        subtitle={subtitle}
        aside={
          <Button variant="primary" onClick={() => nameRef.current?.focus()}>
            + Add candidate
          </Button>
        }
      />

      <div className="split-grid">
        <div className="search-stack">
          <GlassCard padding="sm">
            <SearchBox
              id="candidate-search"
              label="Search candidates"
              placeholder="Search by name, email or skill"
              value={search}
              onChange={handleSearch}
            />
          </GlassCard>

          <QueryBoundary
            query={candidates}
            isEmpty={(list) => list.length === 0}
            emptyMessage={search ? "No candidates match this search." : "No candidates yet. Create the first one."}
            emptyAction={
              search ? (
                <Button onClick={() => setParams({})}>Clear search</Button>
              ) : (
                <Button onClick={() => nameRef.current?.focus()}>Add candidate</Button>
              )
            }
          >
            {(list) => (
              <GlassCard padding="none" className="overflow-hidden">
                <div className="table-scroll">
                  <table className="data-table min-w-[590px]">
                    <thead>
                      <tr>
                        <th scope="col">Candidate</th>
                        <th scope="col">Skills</th>
                        <th scope="col">Experience</th>
                        <th scope="col">Applications</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.map((candidate) => {
                        const hiddenSkills = candidate.skills.length - VISIBLE_SKILLS;
                        return (
                          <tr key={candidate.id}>
                            <td>
                              <Link className="cell-link cell-title" to={`/candidates/${candidate.id}`}>
                                {candidate.name}
                              </Link>
                              <span className="cell-sub">{candidate.email}</span>
                            </td>
                            <td>
                              <div className="skill-list">
                                {candidate.skills.slice(0, VISIBLE_SKILLS).map((skill) => (
                                  <SkillTag key={skill} skill={skill} />
                                ))}
                                {hiddenSkills > 0 && (
                                  <span className="num pl-0.5 text-[13px] text-muted" title={candidate.skills.slice(VISIBLE_SKILLS).join(", ")}>
                                    +{hiddenSkills}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="num whitespace-nowrap">{formatYears(candidate.experience_years)}</td>
                            <td className="num">{candidate.application_count}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            )}
          </QueryBoundary>
        </div>

        <GlassCard as="section" aria-label="Add candidate" className="split-form">
          <h2 className="card-title">Add candidate</h2>
          <div className="mt-[13px]">
            <CandidateForm
              key={formKey}
              ref={nameRef}
              submitLabel="Save candidate"
              isSubmitting={createCandidate.isPending}
              serverError={createCandidate.error}
              onSubmit={(input) => createCandidate.mutate(input, { onSuccess: resetForm })}
              onCancel={resetForm}
            />
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

import { useCallback, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useCandidates, useCreateCandidate } from "../api/candidates";
import { CandidateForm } from "../components/CandidateForm";
import { Modal } from "../components/Modal";
import { QueryBoundary } from "../components/QueryBoundary";
import { SearchBox } from "../components/SearchBox";
import { formatYears } from "../lib/format";

export function CandidatesPage() {
  const [params, setParams] = useSearchParams();
  const search = params.get("search") ?? "";
  const candidates = useCandidates(search);
  const createCandidate = useCreateCandidate();
  const [isCreating, setIsCreating] = useState(false);

  const handleSearch = useCallback(
    (value: string) => setParams(value ? { search: value } : {}),
    [setParams],
  );

  function closeForm() {
    setIsCreating(false);
    createCandidate.reset();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Candidates</h1>
        <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
          New candidate
        </button>
      </div>

      <div className="max-w-md">
        <SearchBox label="Search candidates" placeholder="Search name, email or skill" value={search} onChange={handleSearch} />
      </div>

      <div className="card overflow-hidden">
        <QueryBoundary
          query={candidates}
          isEmpty={(list) => list.length === 0}
          emptyMessage={search ? "No candidates match this search." : "No candidates yet. Create the first one."}
        >
          {(list) => (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-4 py-2">Name</th>
                    <th className="px-4 py-2">Email</th>
                    <th className="px-4 py-2">Experience</th>
                    <th className="px-4 py-2">Skills</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {list.map((candidate) => (
                    <tr key={candidate.id}>
                      <td className="whitespace-nowrap px-4 py-2">
                        <Link className="link" to={`/candidates/${candidate.id}`}>
                          {candidate.name}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-gray-600">{candidate.email}</td>
                      <td className="whitespace-nowrap px-4 py-2 text-gray-600">{formatYears(candidate.experience_years)}</td>
                      <td className="px-4 py-2 text-gray-600">{candidate.skills.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryBoundary>
      </div>

      {isCreating && (
        <Modal title="New candidate" onClose={closeForm}>
          <CandidateForm
            submitLabel="Create candidate"
            isSubmitting={createCandidate.isPending}
            serverError={createCandidate.error}
            onSubmit={(input) => createCandidate.mutate(input, { onSuccess: closeForm })}
            onCancel={closeForm}
          />
        </Modal>
      )}
    </div>
  );
}

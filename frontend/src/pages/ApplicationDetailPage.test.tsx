import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { ApplicationDetail } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders, type MockHandler } from "../test/helpers";
import { ApplicationDetailPage } from "./ApplicationDetailPage";

function makeDetail(overrides: Partial<ApplicationDetail> = {}): ApplicationDetail {
  return {
    id: 7,
    candidate_id: 10,
    candidate_name: "Ada Candidate",
    candidate_email: "ada@example.com",
    candidate_experience_years: 0.25,
    job_id: 20,
    job_title: "Node Intern",
    required_matched: 3,
    required_total: 3,
    status: "Applied",
    version: 3,
    created_at: "2026-11-02T10:14:00Z",
    updated_at: "2026-11-02T10:14:00Z",
    prediction: { label: "Potential Match", probability: 0.89, model_version: "abc123", computed_at: "2026-11-04T00:00:00Z" },
    prediction_message: null,
    top_features: [
      { feature: "required_overlap_ratio", value: 1, contribution: 0.31 },
      { feature: "skill_jaccard", value: 0.44, contribution: 0.09 },
      { feature: "experience_gap", value: -0.75, contribution: -0.06 },
    ],
    candidate_profile_summary: "Built an API.",
    job_min_experience_years: 1,
    experience_gap: -0.75,
    required_skills_matched: ["javascript", "nodejs", "sql"],
    required_skills_missing: [],
    preferred_skills_matched: ["postgresql"],
    preferred_skills_missing: ["docker"],
    other_candidate_skills: ["react"],
    imported_from_dataset: true,
    ...overrides,
  };
}

function renderDetail(handler: MockHandler) {
  const fetchMock = mockFetch((url, init) => {
    if (url.pathname.endsWith("/history")) return jsonResponse([]);
    return handler(url, init);
  });
  renderWithProviders(
    <Routes>
      <Route path="/applications/:id" element={<ApplicationDetailPage />} />
      <Route path="/applications" element={<div>Applications list</div>} />
    </Routes>,
    "/applications/7",
  );
  return fetchMock;
}

describe("ApplicationDetailPage", () => {
  it("splits the skills into matched and missing, and explains the score in plain words", async () => {
    renderDetail(() => jsonResponse(makeDetail()));

    expect(await screen.findByText("Required · 3 of 3")).toBeInTheDocument();
    expect(screen.getByText("Preferred · 1 of 2")).toBeInTheDocument();
    expect(screen.getByText("docker")).toHaveClass("skill-tag-miss");
    expect(screen.getByText("postgresql")).toHaveClass("skill-tag-hit");
    expect(screen.getByText("react")).not.toHaveClass("skill-tag-hit");

    expect(screen.getByText("Required skills matched")).toBeInTheDocument();
    expect(screen.getByText("3 of 3")).toBeInTheDocument();
    expect(screen.getByText("+31 pts")).toHaveClass("text-ok");
    expect(screen.getByText("−6 pts")).toHaveClass("text-warn");
    expect(screen.getByText("89%")).toBeInTheDocument();
    expect(screen.getByText("Advisory only. The model never changes the status.")).toBeInTheDocument();
  });

  it("shows a negative experience gap as a warning", async () => {
    renderDetail(() => jsonResponse(makeDetail()));

    expect(await screen.findByText("−0.75 yr", { selector: "dd" })).toHaveClass("text-warn");
  });

  it("explains itself when no prediction is available", async () => {
    renderDetail(() =>
      jsonResponse(makeDetail({ prediction: null, top_features: [], prediction_message: "The model file is missing." })),
    );

    expect(await screen.findByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("The model file is missing.")).toBeInTheDocument();
    expect(screen.queryByText("Why this score")).not.toBeInTheDocument();
  });

  it("sends the version it read when the segmented control changes status", async () => {
    let stored = makeDetail();
    const fetchMock = renderDetail((_url, init) => {
      if (init?.method === "PATCH") {
        stored = { ...stored, status: "Shortlisted", version: 4 };
        return jsonResponse(stored);
      }
      return jsonResponse(stored);
    });

    const group = await screen.findByRole("group", { name: "Set status" });
    expect(within(group).getByRole("button", { name: "Applied" })).toHaveAttribute("aria-pressed", "true");

    await userEvent.setup().click(within(group).getByRole("button", { name: "Shortlisted" }));

    await waitFor(() => expect(within(group).getByRole("button", { name: "Shortlisted" })).toHaveAttribute("aria-pressed", "true"));
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH")!;
    expect(JSON.parse(String(patch[1]!.body))).toEqual({ status: "Shortlisted", version: 3 });
  });

  it("on a stale update, reloads the record and asks the recruiter to review", async () => {
    let loads = 0;
    renderDetail((_url, init) => {
      if (init?.method === "PATCH") {
        return jsonResponse({ detail: "Changed by someone else.", code: "STALE_UPDATE" }, 409);
      }
      loads += 1;
      return jsonResponse(loads === 1 ? makeDetail() : makeDetail({ status: "Rejected", version: 4 }));
    });

    const group = await screen.findByRole("group", { name: "Set status" });
    await userEvent.setup().click(within(group).getByRole("button", { name: "Shortlisted" }));

    expect(await screen.findByText("This record was changed, please review.")).toBeInTheDocument();
    await waitFor(() => expect(within(group).getByRole("button", { name: "Rejected" })).toHaveAttribute("aria-pressed", "true"));
  });

  it("soft-deletes with the version it read, then returns to the list", async () => {
    vi.stubGlobal("confirm", () => true);
    const fetchMock = renderDetail((_url, init) => {
      if (init?.method === "DELETE") return new Response(null, { status: 204 });
      return jsonResponse(makeDetail());
    });

    await userEvent.setup().click(await screen.findByRole("button", { name: "Delete application" }));

    expect(await screen.findByText("Applications list")).toBeInTheDocument();
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === "DELETE")!;
    expect(new URL(String(request[0])).searchParams.get("version")).toBe("3");
  });
});

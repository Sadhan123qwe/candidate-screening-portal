import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { Job } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/helpers";
import { JobsPage } from "./JobsPage";

const JOB: Job = {
  id: 1,
  external_ref: null,
  title: "React Intern",
  description: "",
  min_experience_years: 0.5,
  required_skills: ["javascript", "react"],
  preferred_skills: [],
  version: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  application_counts: { Applied: 40, Shortlisted: 1, Rejected: 1 },
};

describe("JobsPage", () => {
  it("lists jobs with their skills, minimum experience and total applications", async () => {
    mockFetch(() => jsonResponse([JOB]));
    renderWithProviders(<JobsPage />);

    expect(await screen.findByRole("link", { name: "React Intern" })).toHaveAttribute("href", "/jobs/1");
    expect(screen.getByText("1 open internship. Required skills drive the prediction most.")).toBeInTheDocument();
    expect(screen.getByText("javascript")).toHaveClass("skill-tag");
    expect(screen.getByText("0.5 yr")).toHaveClass("num");
    expect(screen.getByText("42")).toHaveClass("num");
  });

  it("shows a skill that is both required and preferred as an inline error, and doesn't submit", async () => {
    const fetchMock = mockFetch(() => jsonResponse([JOB]));
    renderWithProviders(<JobsPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Title"), "Backend Intern");
    await user.type(screen.getByLabelText("Required skills"), "go,sql,");
    await user.type(screen.getByLabelText("Preferred skills"), "SQL{Enter}");

    const preferred = screen.getByLabelText("Preferred skills");
    const message = "sql is already a required skill. Remove it from one list.";
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(preferred).toHaveAccessibleDescription(message);

    await user.click(screen.getByRole("button", { name: "Create job" }));
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("creates a job from the form, then clears it", async () => {
    const fetchMock = mockFetch((_url, init) => (init?.method === "POST" ? jsonResponse({ ...JOB, id: 2 }, 201) : jsonResponse([JOB])));
    renderWithProviders(<JobsPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Title"), "Backend Intern");
    await user.type(screen.getByLabelText("Required skills"), "go{Enter}sql{Enter}");
    await user.type(screen.getByLabelText("Preferred skills"), "docker");
    await user.click(screen.getByRole("button", { name: "Create job" }));

    await waitFor(() => expect(screen.getByLabelText("Title")).toHaveValue(""));
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")!;
    expect(JSON.parse(String(post[1]!.body))).toEqual({
      title: "Backend Intern",
      description: "",
      min_experience_years: 0,
      required_skills: ["go", "sql"],
      preferred_skills: ["docker"],
    });
  });

  it("removes a skill tag with its button or Backspace", async () => {
    mockFetch(() => jsonResponse([JOB]));
    renderWithProviders(<JobsPage />);
    const user = userEvent.setup();
    const form = screen.getByRole("region", { name: "New job" });

    await user.type(screen.getByLabelText("Required skills"), "go{Enter}sql{Enter}rust{Enter}");
    await user.click(within(form).getByRole("button", { name: "Remove sql" }));
    expect(within(form).queryByText("sql")).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Required skills"), "{Backspace}");
    expect(within(form).queryByText("rust")).not.toBeInTheDocument();
    expect(within(form).getByText("go")).toBeInTheDocument();
  });

  it("sends people to the form from the header button", async () => {
    mockFetch(() => jsonResponse([JOB]));
    renderWithProviders(<JobsPage />);

    await userEvent.setup().click(screen.getByRole("button", { name: "+ New job" }));

    expect(screen.getByLabelText("Title")).toHaveFocus();
  });

  it("shows the empty state with a way forward", async () => {
    mockFetch(() => jsonResponse([]));
    renderWithProviders(<JobsPage />);

    expect(await screen.findByText("No jobs yet. Create the first one.")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "New job" }));
    expect(screen.getByLabelText("Title")).toHaveFocus();
  });
});

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { Candidate } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/helpers";
import { CandidatesPage } from "./CandidatesPage";

const CANDIDATE: Candidate = {
  id: 1,
  external_ref: null,
  name: "Ada Candidate",
  email: "ada@example.com",
  experience_years: 1.5,
  profile_summary: "",
  skills: ["css", "docker", "git", "go", "python", "sql"],
  version: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  application_count: 2,
};

describe("CandidatesPage", () => {
  it("shows the first four skills with a count of the rest, plus experience and applications", async () => {
    mockFetch(() => jsonResponse([CANDIDATE]));
    renderWithProviders(<CandidatesPage />);

    expect(await screen.findByRole("link", { name: "Ada Candidate" })).toHaveAttribute("href", "/candidates/1");
    expect(screen.getByText("go")).toHaveClass("skill-tag");
    expect(screen.queryByText("python")).not.toBeInTheDocument();
    expect(screen.getByText("+2")).toHaveAttribute("title", "python, sql");
    expect(screen.getByText("1.5 yr")).toHaveClass("num");
    expect(screen.getByText("2")).toHaveClass("num");
    expect(screen.getByText(/^1 candidates\./)).toBeInTheDocument();
  });

  it("reads the search from the URL and sends it to the API", async () => {
    const fetchMock = mockFetch(() => jsonResponse([CANDIDATE]));
    renderWithProviders(<CandidatesPage />, "/?search=ada");

    await screen.findByRole("link", { name: "Ada Candidate" });

    expect(new URL(String(fetchMock.mock.calls[0][0])).searchParams.get("search")).toBe("ada");
    expect(screen.getByRole("searchbox", { name: "Search candidates" })).toHaveValue("ada");
  });

  it("validates inline, linking each message to its field, without calling the server", async () => {
    const fetchMock = mockFetch(() => jsonResponse([]));
    renderWithProviders(<CandidatesPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Email"), "priya.nair@");
    await user.click(screen.getByRole("button", { name: "Save candidate" }));

    const email = screen.getByLabelText("Email");
    expect(email).toHaveAccessibleDescription("Enter a full email address, like name@company.com.");
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveClass("control-error");
    expect(screen.getByText("Full name is required.")).toBeInTheDocument();
    expect(screen.getByText("Enter at least one skill.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("shows a duplicate email from the server, keeping what was typed", async () => {
    mockFetch((_url, init) =>
      init?.method === "POST"
        ? jsonResponse({ detail: "A candidate with the email ada@example.com already exists.", code: "DUPLICATE_EMAIL" }, 409)
        : jsonResponse([]),
    );
    renderWithProviders(<CandidatesPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Full name"), "Ada Two");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Experience (years)"), "1");
    await user.type(screen.getByLabelText("Skills"), "python{Enter}");
    await user.click(screen.getByRole("button", { name: "Save candidate" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
    expect(screen.getByLabelText("Full name")).toHaveValue("Ada Two");
  });

  it("saves a skill still being typed when the form is submitted", async () => {
    const fetchMock = mockFetch((_url, init) => (init?.method === "POST" ? jsonResponse({ ...CANDIDATE, id: 2 }, 201) : jsonResponse([])));
    renderWithProviders(<CandidatesPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Full name"), "Ada Two");
    await user.type(screen.getByLabelText("Email"), "ada2@example.com");
    await user.type(screen.getByLabelText("Experience (years)"), "1");
    await user.type(screen.getByLabelText("Skills"), "python");
    await user.click(screen.getByRole("button", { name: "Save candidate" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(true));
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")!;
    expect(JSON.parse(String(post[1]!.body)).skills).toEqual(["python"]);
  });
});

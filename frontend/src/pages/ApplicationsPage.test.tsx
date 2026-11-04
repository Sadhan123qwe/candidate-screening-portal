import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { Application, ApplicationPage } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders, type MockHandler } from "../test/helpers";
import { ApplicationsPage } from "./ApplicationsPage";

function makeApplication(overrides: Partial<Application> = {}): Application {
  return {
    id: 1,
    candidate_id: 10,
    candidate_name: "Ada Candidate",
    candidate_email: "ada@example.com",
    candidate_experience_years: 1.5,
    job_id: 20,
    job_title: "React Intern",
    required_matched: 2,
    required_total: 3,
    status: "Applied",
    version: 1,
    created_at: "2026-01-15T10:00:00Z",
    updated_at: "2026-01-15T10:00:00Z",
    prediction: {
      label: "Potential Match",
      probability: 0.87,
      model_version: "abc",
      computed_at: "2026-01-15T10:00:00Z",
    },
    prediction_message: null,
    ...overrides,
  };
}

function pageOf(items: Application[]): ApplicationPage {
  return { items, total: items.length, page: 1, page_size: 25 };
}

const SUMMARY = { total: 7, applied: 4, shortlisted: 2, rejected: 1 };

/** Answers the page's supporting requests, and lets each test decide how applications respond. */
function mockApi(applications: MockHandler) {
  return mockFetch((url, init) => {
    if (url.pathname === "/api/jobs") return jsonResponse([]);
    if (url.pathname === "/api/stats") return jsonResponse({ jobs: 10, candidates: 250, applications: 500 });
    if (url.pathname === "/api/applications/summary") return jsonResponse(SUMMARY);
    return applications(url, init);
  });
}

describe("ApplicationsPage", () => {
  it("shows the loading state and then the rows", async () => {
    let respond: (response: Response) => void = () => {};
    const pending = new Promise<Response>((resolve) => {
      respond = resolve;
    });
    mockApi(() => pending);
    renderWithProviders(<ApplicationsPage />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading...");

    respond(jsonResponse(pageOf([makeApplication()])));

    expect(await screen.findByRole("link", { name: "Ada Candidate" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "React Intern" })).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows prediction badges, with the probability on hover", async () => {
    mockApi(() =>
      jsonResponse(
        pageOf([
          makeApplication(),
          makeApplication({
            id: 2,
            candidate_name: "No Model",
            prediction: null,
            prediction_message: "Prediction unavailable: the model file is missing.",
          }),
        ]),
      ),
    );
    renderWithProviders(<ApplicationsPage />);

    const match = await screen.findByText("Potential Match", { selector: "span" });
    expect(match).toHaveAttribute("title", "Probability of a match: 87%");
    expect(match).toHaveClass("badge-ok");
    expect(within(match).getByText("87%")).toHaveClass("num");

    const unavailable = screen.getByText("Unavailable");
    expect(unavailable).toHaveAttribute("title", "Prediction unavailable: the model file is missing.");
    expect(unavailable).toHaveClass("badge-none");
  });

  it("shows the empty state", async () => {
    mockApi(() => jsonResponse(pageOf([])));
    renderWithProviders(<ApplicationsPage />);

    expect(await screen.findByText("No applications match these filters.")).toBeInTheDocument();
  });

  it("shows an error with a retry button that works", async () => {
    let shouldFail = true;
    mockApi(() =>
      shouldFail
        ? jsonResponse({ detail: "A database error occurred.", code: "DB_ERROR" }, 500)
        : jsonResponse(pageOf([makeApplication()])),
    );
    renderWithProviders(<ApplicationsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("A database error occurred.");

    shouldFail = false;
    await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("link", { name: "Ada Candidate" })).toBeInTheDocument();
  });

  it("reads filters from the URL and sends them to the API", async () => {
    const fetchMock = mockApi(() => jsonResponse(pageOf([makeApplication()])));
    renderWithProviders(<ApplicationsPage />, "/?status=Shortlisted&search=ada&prediction=Needs+Review&page=2");

    await screen.findByRole("link", { name: "Ada Candidate" });

    const request = fetchMock.mock.calls
      .map(([input]) => new URL(String(input)))
      .find((url) => url.pathname === "/api/applications")!;
    expect(request.searchParams.get("status")).toBe("Shortlisted");
    expect(request.searchParams.get("search")).toBe("ada");
    expect(request.searchParams.get("prediction")).toBe("Needs Review");
    expect(request.searchParams.get("page")).toBe("2");
    expect(screen.getByRole("combobox", { name: "Filter by prediction" })).toHaveValue("Needs Review");
    expect(screen.getByRole("combobox", { name: "Filter by status" })).toHaveValue("Shortlisted");
  });

  it("shows status counts on the chips, and filters when one is clicked", async () => {
    const fetchMock = mockApi(() => jsonResponse(pageOf([makeApplication()])));
    renderWithProviders(<ApplicationsPage />);
    await screen.findByRole("link", { name: "Ada Candidate" });

    const shortlisted = await screen.findByRole("button", { name: "Shortlisted 2" });
    expect(screen.getByRole("button", { name: "All 7" })).toHaveAttribute("aria-pressed", "true");

    await userEvent.setup().click(shortlisted);

    await waitFor(() => expect(shortlisted).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByRole("combobox", { name: "Filter by status" })).toHaveValue("Shortlisted");
    await waitFor(() => {
      const urls = fetchMock.mock.calls.map(([input]) => new URL(String(input)));
      expect(urls.some((url) => url.pathname === "/api/applications" && url.searchParams.get("status") === "Shortlisted")).toBe(true);
    });
  });

  it("passes the job filter to the status counts", async () => {
    const fetchMock = mockApi(() => jsonResponse(pageOf([makeApplication()])));
    renderWithProviders(<ApplicationsPage />, "/?job_id=20");
    await screen.findByRole("link", { name: "Ada Candidate" });

    const summary = fetchMock.mock.calls
      .map(([input]) => new URL(String(input)))
      .find((url) => url.pathname === "/api/applications/summary")!;
    expect(summary.searchParams.get("job_id")).toBe("20");
  });

  it("shows the required skill match and experience on each row", async () => {
    mockApi(() => jsonResponse(pageOf([makeApplication()])));
    renderWithProviders(<ApplicationsPage />);

    expect(await screen.findByText("2 / 3")).toHaveClass("num");
    expect(screen.getByText("1.5 yr")).toHaveClass("num");
    expect(screen.getByText("ada@example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open application: Ada Candidate/ })).toHaveAttribute("href", "/applications/1");
  });

  it("sends the version it read when changing status, and updates the row in place", async () => {
    let stored = makeApplication({ version: 3 });
    const fetchMock = mockApi((_url, init) => {
      if (init?.method === "PATCH") {
        stored = { ...stored, status: "Shortlisted", version: 4 };
        return jsonResponse(stored);
      }
      return jsonResponse(pageOf([stored]));
    });
    renderWithProviders(<ApplicationsPage />);

    const select = await screen.findByRole("combobox", { name: "Status for Ada Candidate" });
    await userEvent.setup().selectOptions(select, "Shortlisted");

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Status for Ada Candidate" })).toHaveValue("Shortlisted"));
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH")!;
    expect(JSON.parse(String(patch[1]!.body))).toEqual({ status: "Shortlisted", version: 3 });
  });

  it("on a stale update, reloads the row and asks the recruiter to review", async () => {
    // Another recruiter has already rejected this application.
    let loads = 0;
    mockApi((_url, init) => {
      if (init?.method === "PATCH") {
        return jsonResponse({ detail: "Changed by someone else.", code: "STALE_UPDATE" }, 409);
      }
      loads += 1;
      return jsonResponse(
        pageOf([loads === 1 ? makeApplication({ version: 1 }) : makeApplication({ status: "Rejected", version: 2 })]),
      );
    });
    renderWithProviders(<ApplicationsPage />);

    const select = await screen.findByRole("combobox", { name: "Status for Ada Candidate" });
    await userEvent.setup().selectOptions(select, "Shortlisted");

    expect(await screen.findByText("This record was changed, please review.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Status for Ada Candidate" })).toHaveValue("Rejected"));
  });

  it("shows the duplicate message inline in the assign modal", async () => {
    mockFetch((url, init) => {
      if (url.pathname === "/api/jobs") {
        return jsonResponse([{ id: 20, title: "React Intern" }]);
      }
      if (url.pathname === "/api/candidates") {
        return jsonResponse([{ id: 10, name: "Ada Candidate", email: "ada@example.com" }]);
      }
      if (init?.method === "POST") {
        return jsonResponse({ detail: "This candidate has already applied to this job.", code: "DUPLICATE_APPLICATION" }, 409);
      }
      return jsonResponse(pageOf([]));
    });
    renderWithProviders(<ApplicationsPage />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "+ Assign candidate" }));
    const dialog = await screen.findByRole("dialog");
    await user.selectOptions(await within(dialog).findByLabelText("Candidate"), "10");
    await user.selectOptions(within(dialog).getByLabelText("Job"), "20");
    await user.click(within(dialog).getByRole("button", { name: "Assign" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("already applied");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

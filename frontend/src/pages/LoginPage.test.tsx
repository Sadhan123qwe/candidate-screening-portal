import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Route, Routes } from "react-router-dom";
import { getToken } from "../api/client";
import { jsonResponse, mockFetch, renderWithProviders, type MockHandler } from "../test/helpers";
import { LoginPage } from "./LoginPage";

function renderLogin() {
  renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/applications" element={<div>Applications screen</div>} />
    </Routes>,
    "/login",
  );
}

async function submitCredentials(email: string, password: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Log in" }));
}

/** The page also asks for the public totals, which every test answers the same way. */
function mockLoginApi(login: MockHandler) {
  return mockFetch((url, init) => {
    if (url.pathname === "/api/stats") return jsonResponse({ jobs: 10, candidates: 250, applications: 500 });
    return login(url, init);
  });
}

describe("LoginPage", () => {
  it("explains bad credentials under the password and stays on the form", async () => {
    mockLoginApi(() => jsonResponse({ detail: "Incorrect email or password.", code: "INVALID_CREDENTIALS" }, 401));
    renderLogin();

    await submitCredentials("recruiter@demo.com", "wrong-password");

    const message = await screen.findByRole("alert");
    expect(message).toHaveTextContent("Wrong email or password. Check them and try again.");
    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription("Wrong email or password. Check them and try again.");
    expect(getToken()).toBeNull();
    expect(screen.getByRole("button", { name: "Log in" })).toBeEnabled();
  });

  it("stores the token and moves on after a successful login", async () => {
    mockLoginApi(() =>
      jsonResponse({
        access_token: "test-token",
        token_type: "bearer",
        user: { id: 1, email: "recruiter@demo.com", full_name: "Demo Recruiter", role: "recruiter" },
      }),
    );
    renderLogin();

    await submitCredentials("recruiter@demo.com", "Demo@12345");

    expect(await screen.findByText("Applications screen")).toBeInTheDocument();
    expect(getToken()).toBe("test-token");
  });

  it("validates on the client before calling the server", async () => {
    const fetchMock = mockLoginApi(() => jsonResponse({}));
    renderLogin();

    await userEvent.setup().click(screen.getByRole("button", { name: "Log in" }));

    expect(screen.getByText("Email is required.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/auth/login"))).toBe(false);
  });

  it("shows the portal totals from the API", async () => {
    mockLoginApi(() => jsonResponse({}));
    renderLogin();

    expect(await screen.findByText("250")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
  });
});

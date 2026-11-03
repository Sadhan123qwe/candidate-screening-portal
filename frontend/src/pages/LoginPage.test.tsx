import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Route, Routes } from "react-router-dom";
import { getToken } from "../api/client";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/helpers";
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
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginPage", () => {
  it("shows the server's error on bad credentials and stays on the form", async () => {
    mockFetch(() => jsonResponse({ detail: "Incorrect email or password.", code: "INVALID_CREDENTIALS" }, 401));
    renderLogin();

    await submitCredentials("recruiter@demo.com", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
    expect(getToken()).toBeNull();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("stores the token and moves on after a successful login", async () => {
    mockFetch(() =>
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
    const fetchMock = mockFetch(() => jsonResponse({}));
    renderLogin();

    await userEvent.setup().click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByText("Email is required.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

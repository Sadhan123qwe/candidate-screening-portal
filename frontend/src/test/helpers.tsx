import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { createQueryClient } from "../api/queryClient";

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export type MockHandler = (url: URL, init?: RequestInit) => Response | Promise<Response>;

/** Replace fetch, so tests run the real UI and API client against canned responses. */
export function mockFetch(handler: MockHandler) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(new URL(String(input)), init)),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function renderWithProviders(ui: ReactElement, route = "/") {
  return render(
    <QueryClientProvider client={createQueryClient({ retry: false })}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

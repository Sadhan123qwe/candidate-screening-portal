// The one place that talks to the backend: adds the token and turns errors into ApiError.

const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "portal.token";
const LOGIN_PATH = "/api/auth/login";

export const STALE_UPDATE = "STALE_UPDATE";
export const STALE_UPDATE_MESSAGE = "This record was changed, please review.";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isStale(): boolean {
    return this.code === STALE_UPDATE;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | undefined>;
}

function buildUrl(path: string, query: RequestOptions["query"]): string {
  const url = new URL(path, API_URL);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function toApiError(response: Response): Promise<ApiError> {
  // A proxy or crash might not return JSON, and that shouldn't hide the real status.
  const body = await response.json().catch(() => ({}));
  const fieldErrors: Record<string, string> = {};
  for (const error of body.errors ?? []) {
    fieldErrors[error.field] = error.message;
  }
  return new ApiError(
    response.status,
    body.code ?? "UNKNOWN_ERROR",
    body.detail ?? `Request failed with status ${response.status}.`,
    fieldErrors,
  );
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Could not reach the server. Is the backend running?");
  }

  // A 401 anywhere but login means the session has ended. Wrong credentials at login
  // should stay on the form and show their message.
  if (response.status === 401 && path !== LOGIN_PATH) {
    clearToken();
    window.location.assign("/login");
  }

  if (!response.ok) throw await toApiError(response);
  return response;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options);
  if (response.status === 204) return undefined as T;
  return response.json();
}

/** Fetches a file with the login token, which a plain link can't send, and saves it. */
export async function apiDownload(path: string, filename: string, query?: RequestOptions["query"]): Promise<void> {
  const response = await send(path, { query });
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

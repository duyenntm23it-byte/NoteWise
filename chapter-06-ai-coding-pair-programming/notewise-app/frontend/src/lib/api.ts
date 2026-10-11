export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const ACCESS_TOKEN_KEY = "notewise.accessToken";
export const SESSION_CHANGED_EVENT = "notewise:session-changed";

export interface AuthenticatedUser {
  id: string;
  email: string;
  created_at: string;
}

export function saveAccessToken(token: string, user: AuthenticatedUser): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
  window.dispatchEvent(
    new CustomEvent(SESSION_CHANGED_EVENT, { detail: { token, user } }),
  );
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.dispatchEvent(
    new CustomEvent(SESSION_CHANGED_EVENT, { detail: { token: null, user: null } }),
  );
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401 && token) {
    clearAccessToken();
  }
  return response;
}

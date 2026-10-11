import { act, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "../lib/api";
import { AuthProvider, useAuth } from "./session";

function SessionState() {
  const { isLoading, user, logout } = useAuth();

  useEffect(() => {
    if (user) {
      window.sessionUser = user;
    }
  }, [user]);

  return (
    <div>
      <output>{isLoading ? "loading" : user?.email ?? "guest"}</output>
      <button onClick={logout}>Log out</button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("restores a stored token only after verifying it with /me", async () => {
    localStorage.setItem("notewise.accessToken", "valid.jwt");
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "d36af6f4-5fa8-467d-b21f-1f69d79c45b2",
          email: "student@example.com",
          created_at: "2026-10-10T00:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(
      <AuthProvider>
        <SessionState />
      </AuthProvider>,
    );

    expect(await screen.findByText("student@example.com")).toBeVisible();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/me$/),
      expect.objectContaining({
        headers: { Authorization: "Bearer valid.jwt" },
      }),
    );
    expect(localStorage.getItem("notewise.accessToken")).toBe("valid.jwt");
  });

  it("clears a rejected token and remains a guest", async () => {
    localStorage.setItem("notewise.accessToken", "expired.jwt");
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 401 }));
    render(
      <AuthProvider>
        <SessionState />
      </AuthProvider>,
    );

    expect(await screen.findByText("guest")).toBeVisible();
    expect(localStorage.getItem("notewise.accessToken")).toBeNull();
  });

  it("clears the session on logout", async () => {
    localStorage.setItem("notewise.accessToken", "valid.jwt");
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "d36af6f4-5fa8-467d-b21f-1f69d79c45b2",
          email: "student@example.com",
          created_at: "2026-10-10T00:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(
      <AuthProvider>
        <SessionState />
      </AuthProvider>,
    );
    await screen.findByText("student@example.com");

    act(() => screen.getByRole("button", { name: "Log out" }).click());

    await waitFor(() => expect(localStorage.getItem("notewise.accessToken")).toBeNull());
    expect(screen.getByText("guest")).toBeVisible();
  });

  it("attaches the bearer token and clears it after an API 401", async () => {
    localStorage.setItem("notewise.accessToken", "expired.jwt");
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 401 }));

    const response = await apiFetch("/api/v1/private-resource");

    expect(response.status).toBe(401);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/private-resource$/);
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer expired.jwt");
    expect(localStorage.getItem("notewise.accessToken")).toBeNull();
  });
});

declare global {
  interface Window {
    sessionUser?: { email: string };
  }
}

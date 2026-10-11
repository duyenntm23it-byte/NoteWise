import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProtectedLayout from "./layout";
import { AuthProvider } from "../../auth/session";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => "/dashboard",
}));

describe("ProtectedLayout", () => {
  beforeEach(() => {
    replace.mockReset();
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("redirects an unauthenticated visitor to the auth screen", async () => {
    render(
      <AuthProvider>
        <ProtectedLayout>
          <p>Private learning data</p>
        </ProtectedLayout>
      </AuthProvider>,
    );

    expect(await screen.findByText("Sign in to continue")).toBeVisible();
    expect(replace).toHaveBeenCalledWith("/auth?next=%2Fdashboard");
    expect(screen.queryByText("Private learning data")).toBeNull();
  });
});

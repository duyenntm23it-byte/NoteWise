import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthForm } from "./auth-form";

const replace = vi.fn();
const searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => searchParams,
}));

describe("AuthForm", () => {
  beforeEach(() => {
    replace.mockReset();
    searchParams.delete("next");
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows login and register modes and the registration password policy", () => {
    render(<AuthForm />);

    expect(screen.getByRole("heading", { name: "Chào mừng trở lại" })).toBeVisible();
    fireEvent.click(
      within(screen.getByRole("group", { name: "Chọn hình thức xác thực" })).getByRole(
        "button",
        { name: "Đăng ký" },
      ),
    );

    expect(screen.getByRole("heading", { name: "Tạo tài khoản mới" })).toBeVisible();
    expect(screen.getByLabelText(/Mật khẩu/)).toHaveAttribute("minLength", "12");
  });

  it("submits valid registration and stores the access token", async () => {
    const fetchMock = vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "signed.jwt.token",
          token_type: "Bearer",
          expires_in: 900,
          user: {
            id: "d36af6f4-5fa8-467d-b21f-1f69d79c45b2",
            email: "student@example.com",
            created_at: "2026-10-10T00:00:00Z",
          },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    searchParams.set("next", "//attacker.example");
    render(<AuthForm />);
    fireEvent.click(
      within(screen.getByRole("group", { name: "Chọn hình thức xác thực" })).getByRole(
        "button",
        { name: "Đăng ký" },
      ),
    );
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "student@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Mật khẩu/), {
      target: { value: "secure-password-123" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Tạo tài khoản" }).closest("form")!);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/auth\/register$/),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "student@example.com",
          password: "secure-password-123",
        }),
      }),
    );
    expect(localStorage.getItem("notewise.accessToken")).toBe("signed.jwt.token");
  });

  it("submits login to the approved OpenAPI route", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "login.jwt.token",
          token_type: "Bearer",
          expires_in: 900,
          user: {
            id: "d36af6f4-5fa8-467d-b21f-1f69d79c45b2",
            email: "student@example.com",
            created_at: "2026-10-10T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    searchParams.set("next", "/materials?source=dashboard");
    render(<AuthForm />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "student@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Mật khẩu/), {
      target: { value: "correct-password" },
    });
    fireEvent.submit(screen.getByLabelText("Email").closest("form")!);

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/materials?source=dashboard"),
    );
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/auth\/login$/),
      expect.objectContaining({ method: "POST" }),
    );
    expect(localStorage.getItem("notewise.accessToken")).toBe("login.jwt.token");
  });

  it("disables the submit action while the authentication request is pending", () => {
    vi.mocked(fetch).mockReturnValue(new Promise<Response>(() => {}));
    render(<AuthForm />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "student@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Mật khẩu/), {
      target: { value: "correct-password" },
    });
    fireEvent.submit(screen.getByLabelText("Email").closest("form")!);

    expect(screen.getByRole("button", { name: "Đang xử lý…" })).toBeDisabled();
  });

  it("displays a safe login error and does not persist a token", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "UNAUTHENTICATED",
            message: "Invalid email or password.",
            request_id: "c20dc0c0-4931-4e45-8c98-285ea445b313",
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<AuthForm />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "student@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Mật khẩu/), {
      target: { value: "wrong-password" },
    });
    fireEvent.submit(screen.getByLabelText("Email").closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password.",
    );
    expect(localStorage.getItem("notewise.accessToken")).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });
});

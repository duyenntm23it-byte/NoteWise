"use client";

import { useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { API_BASE_URL, saveAccessToken, type AuthenticatedUser } from "../../lib/api";

type AuthMode = "login" | "register";

interface AuthResponse {
  access_token: string;
  token_type: "Bearer";
  expires_in: 900;
  user: AuthenticatedUser;
}

function getSafeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/dashboard";
  }
  return value;
}

export function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const endpoint = mode === "register" ? "register" : "login";
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body = (await response.json()) as AuthResponse | {
        error?: { message?: string };
      };
      if (!response.ok) {
        setError(
          "error" in body && body.error?.message
            ? body.error.message
            : "We could not authenticate your account. Please try again.",
        );
        return;
      }
      if (!("access_token" in body) || !body.access_token || !body.user) {
        throw new Error("The authentication response was incomplete.");
      }
      saveAccessToken(body.access_token, body.user);
      router.replace(getSafeReturnPath(searchParams.get("next")));
    } catch {
      setError("Unable to connect to NoteWise. Please try again.");
    } finally {
      setPending(false);
    }
  }

  const registering = mode === "register";

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">N</span>
          <span>NoteWise</span>
        </div>
        <p className="eyebrow">Không gian học tập cá nhân</p>
        <h1 id="auth-title">
          {registering ? "Tạo tài khoản mới" : "Chào mừng trở lại"}
        </h1>
        <p className="subtle">
          {registering
            ? "Tạo tài khoản để bắt đầu hành trình học tập của bạn."
            : "Đăng nhập để tiếp tục tiến độ học của bạn."}
        </p>

        <div className="auth-tabs" role="group" aria-label="Chọn hình thức xác thực">
          <button
            type="button"
            className={!registering ? "auth-tab active" : "auth-tab"}
            aria-pressed={!registering}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Đăng nhập
          </button>
          <button
            type="button"
            className={registering ? "auth-tab active" : "auth-tab"}
            aria-pressed={registering}
            onClick={() => {
              setMode("register");
              setError(null);
            }}
          >
            Đăng ký
          </button>
        </div>

        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="auth-email">
            Email
            <input
              autoComplete="email"
              id="auth-email"
              name="email"
              type="email"
              placeholder="ban@example.com"
              required
              maxLength={320}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label htmlFor="auth-password">
            Mật khẩu
            <span className="password-control">
              <input
                autoComplete={registering ? "new-password" : "current-password"}
                id="auth-password"
                name="password"
                type={showPassword ? "text" : "password"}
                required
                minLength={registering ? 12 : undefined}
                maxLength={registering ? 128 : undefined}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className="password-toggle"
                aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? "Ẩn" : "Hiện"}
              </button>
            </span>
            {registering && (
              <span className="field-hint">Mật khẩu cần từ 12 đến 128 ký tự.</span>
            )}
          </label>
          {error && (
            <p className="auth-error" role="alert" aria-live="assertive">
              {error}
            </p>
          )}
          <button className="submit-button" type="submit" disabled={pending}>
            {pending
              ? "Đang xử lý…"
              : registering
                ? "Tạo tài khoản"
                : "Đăng nhập"}
          </button>
        </form>
        <p className="auth-note">
          Chưa đăng nhập sẽ không thể truy cập tài liệu riêng tư.
        </p>
      </section>
    </main>
  );
}

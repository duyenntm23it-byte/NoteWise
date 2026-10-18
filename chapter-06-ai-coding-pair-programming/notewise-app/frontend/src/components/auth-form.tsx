"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { useAuth } from "@/components/auth-provider";

type AuthMode = "login" | "register";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const { user, isLoading, login, register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isRegister = mode === "register";

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/");
    }
  }, [isLoading, router, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (isRegister) {
        await register(email.trim(), password);
      } else {
        await login(email.trim(), password);
      }
      router.replace("/");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-slate-50 lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 px-12 py-10 text-white lg:flex lg:flex-col lg:justify-between xl:px-20">
        <div
          aria-hidden="true"
          className="absolute -right-28 top-24 h-96 w-96 rounded-full bg-indigo-500/20 blur-3xl"
        />
        <Link href="/" className="relative flex items-center gap-3 text-xl font-bold">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-500 text-lg">
            N
          </span>
          NoteWise
        </Link>
        <div className="relative max-w-xl pb-12">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-indigo-300">
            Your learning, in focus
          </p>
          <h1 className="mt-5 text-5xl font-semibold leading-tight tracking-tight xl:text-6xl">
            Make every idea count.
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-300">
            Bring your learning materials, quizzes, and progress together in one thoughtful
            workspace.
          </p>
          <div className="mt-10 flex gap-2" aria-hidden="true">
            <span className="h-1.5 w-10 rounded-full bg-indigo-400" />
            <span className="h-1.5 w-5 rounded-full bg-slate-700" />
            <span className="h-1.5 w-5 rounded-full bg-slate-700" />
          </div>
        </div>
        <p className="relative text-sm text-slate-400">A calmer way to learn with intention.</p>
      </section>

      <section className="flex items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-md">
          <Link href="/" className="mb-12 flex items-center gap-3 text-lg font-bold lg:hidden">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-white">
              N
            </span>
            NoteWise
          </Link>
          <p className="text-sm font-semibold text-brand">
            {isRegister ? "START YOUR WORKSPACE" : "WELCOME BACK"}
          </p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-ink">
            {isRegister ? "Create your account" : "Sign in to NoteWise"}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            {isRegister
              ? "Set up your personal learning space in just a moment."
              : "Pick up where your learning left off."}
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                maxLength={320}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-brand focus:ring-4 focus:ring-indigo-100"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                required
                minLength={12}
                maxLength={128}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-slate-400 focus:border-brand focus:ring-4 focus:ring-indigo-100"
                placeholder="At least 12 characters"
              />
              {isRegister && (
                <p className="mt-2 text-xs text-slate-500">
                  Use at least 12 characters. Passwords are securely hashed.
                </p>
              )}
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isSubmitting || isLoading}
              className="flex w-full items-center justify-center rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting
                ? "Please wait…"
                : isRegister
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>

          <p className="mt-7 text-center text-sm text-slate-500">
            {isRegister ? "Already have an account?" : "New to NoteWise?"}{" "}
            <Link
              href={isRegister ? "/login" : "/register"}
              className="font-semibold text-brand hover:underline"
            >
              {isRegister ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}

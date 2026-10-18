"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth-provider";
import { AppShell } from "@/components/app-shell";

const destinations = [
  {
    title: "Material Hub",
    description: "Organize learning materials and ask questions grounded in your notes.",
    href: "/materials",
    label: "Explore your materials",
    icon: "▤",
    style: "bg-indigo-100 text-indigo-700",
  },
  {
    title: "AI Quiz Player",
    description: "Practice what you know with focused quizzes from your study material.",
    href: "/quiz",
    label: "Start a practice session",
    icon: "✳",
    style: "bg-amber-100 text-amber-700",
  },
  {
    title: "Analytics Dashboard",
    description: "Review learning progress and discover topics that need more attention.",
    href: "/analytics",
    label: "Review your progress",
    icon: "▥",
    style: "bg-emerald-100 text-emerald-700",
  },
];

export default function HomePage() {
  const router = useRouter();
  const { user, isLoading, sessionError } = useAuth();

  useEffect(() => {
    if (!isLoading && !user && !sessionError) {
      router.replace("/login");
    }
  }, [isLoading, router, sessionError, user]);

  if (!user) {
    if (sessionError) {
      return (
        <main className="grid min-h-screen place-items-center bg-slate-50 px-5">
          <section
            role="alert"
            className="max-w-lg rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-sm"
          >
            <h1 className="text-xl font-semibold text-ink">Could not restore your session</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">{sessionError}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-6 rounded-xl bg-brand px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              Try again
            </button>
          </section>
        </main>
      );
    }
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50">
        <p className="text-sm font-medium text-slate-500" role="status">
          Loading your workspace…
        </p>
      </main>
    );
  }

  return (
    <AppShell>
      <section>
        <p className="text-sm font-semibold text-brand">YOUR LEARNING WORKSPACE</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          Welcome back
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-500">
          Choose a space to continue learning. Your materials, practice, and progress are all
          connected.
        </p>
      </section>

      <section aria-label="Learning spaces" className="mt-9 grid gap-5 lg:grid-cols-3">
        {destinations.map((destination) => (
          <article
            key={destination.title}
            className="group flex min-h-72 flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-lg hover:shadow-indigo-950/5"
          >
            <span
              aria-hidden="true"
              className={`grid h-12 w-12 place-items-center rounded-xl text-xl ${destination.style}`}
            >
              {destination.icon}
            </span>
            <h2 className="mt-6 text-lg font-semibold text-ink">{destination.title}</h2>
            <p className="mt-2 flex-1 text-sm leading-6 text-slate-500">
              {destination.description}
            </p>
            <Link
              href={destination.href}
              className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-brand focus:outline-none focus:ring-4 focus:ring-indigo-100"
            >
              {destination.label}
              <span
                aria-hidden="true"
                className="transition-transform group-hover:translate-x-1"
              >
                →
              </span>
            </Link>
          </article>
        ))}
      </section>

      <section className="mt-8 rounded-2xl border border-indigo-100 bg-indigo-50/70 p-6 sm:flex sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-indigo-950">A fresh start</p>
          <p className="mt-1 text-sm text-indigo-800/80">
            Your personal workspace is ready for your next study session.
          </p>
        </div>
        <span className="mt-4 inline-flex rounded-full bg-white px-3 py-1.5 text-xs font-medium text-indigo-700 sm:mt-0">
          Signed in as {user.email}
        </span>
      </section>
    </AppShell>
  );
}

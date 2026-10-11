"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "../../../auth/session";

function Icon({ children, className = "h-5 w-5" }: { children: ReactNode; className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      {children}
    </svg>
  );
}

const navigation = [
  {
    href: "/dashboard",
    label: "Overview",
    icon: (
      <>
        <rect height="7" rx="1.5" width="7" x="3" y="3" />
        <rect height="7" rx="1.5" width="7" x="14" y="3" />
        <rect height="7" rx="1.5" width="7" x="14" y="14" />
        <rect height="7" rx="1.5" width="7" x="3" y="14" />
      </>
    ),
  },
  {
    href: "/documents",
    label: "My materials",
    icon: (
      <>
        <path d="M5 3.75h9l5 5v11.5H5z" />
        <path d="M14 3.75v5h5M8 13h8M8 16.5h8" />
      </>
    ),
  },
  {
    href: "/analytics",
    label: "Learning analytics",
    icon: (
      <>
        <path d="M4 19V5M4 19h16" />
        <path d="m7 15 4-4 3 2 5-6" />
      </>
    ),
  },
  {
    href: "/history",
    label: "Learning history",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3.5 2" />
      </>
    ),
  },
];

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function signOut() {
    logout();
    router.replace("/auth");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950 px-5 py-6 text-slate-300 lg:flex">
        <Link aria-label="NoteWise home" className="mb-12 flex items-center gap-3 px-2" href="/dashboard">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-amber-400 text-slate-950">
            <Icon className="h-5 w-5">
              <path d="M5 4.5h9l5 5v10H5z" />
              <path d="M14 4.5v5h5M8 13h8M8 16.5h5" />
            </Icon>
          </span>
          <span className="text-lg font-semibold tracking-tight text-white">NoteWise</span>
        </Link>

        <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
          Workspace
        </p>
        <nav aria-label="Main navigation" className="space-y-1">
          {navigation.map((item, index) => (
            <Link
              aria-current={index === 0 ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                index === 0
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-900 hover:text-white"
              }`}
              href={item.href}
              key={item.href}
            >
              <Icon>{item.icon}</Icon>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="mt-auto rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <p className="text-sm font-semibold text-white">Study at your pace</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            Your notes and learning progress, together in one place.
          </p>
        </div>
        <button
          className="mt-4 flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-slate-400 transition hover:bg-slate-900 hover:text-white"
          onClick={signOut}
          type="button"
        >
          <Icon>
            <path d="M10 17l5-5-5-5M15 12H3" />
            <path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" />
          </Icon>
          Sign out
        </button>
      </aside>

      <main className="min-w-0 flex-1">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4 sm:px-8 lg:px-10">
          <Link className="flex items-center gap-2 font-semibold text-slate-950 lg:hidden" href="/dashboard">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-amber-400 text-slate-950">
              <Icon className="h-4 w-4">
                <path d="M5 4.5h9l5 5v10H5z" />
                <path d="M14 4.5v5h5M8 13h8M8 16.5h5" />
              </Icon>
            </span>
            NoteWise
          </Link>
          <div className="hidden text-sm text-slate-500 lg:block">Personal learning workspace</div>
          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-slate-800">{user?.email}</p>
              <p className="text-xs text-slate-500">Student workspace</p>
            </div>
            <span
              aria-label={user?.email ? `Signed in as ${user.email}` : "Signed in"}
              className="grid h-10 w-10 place-items-center rounded-full bg-amber-100 text-sm font-bold uppercase text-amber-900"
            >
              {user?.email?.slice(0, 1) ?? "S"}
            </span>
            <button
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 lg:hidden"
              onClick={signOut}
              type="button"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10 lg:px-10">
          <section className="mb-9 flex flex-col justify-between gap-6 rounded-3xl bg-slate-950 px-6 py-8 text-white shadow-xl shadow-slate-900/10 sm:px-9 sm:py-10 md:flex-row md:items-center">
            <div className="max-w-2xl">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-amber-300">
                Your learning, in one place
              </p>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Welcome back{user?.email ? `, ${user.email.split("@")[0]}` : ""}.
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
                Pick up where you left off, explore your study materials, or see how far you have come.
              </p>
            </div>
            <Link
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-300 focus:ring-offset-2 focus:ring-offset-slate-950"
              href="/documents"
            >
              <Icon className="h-4 w-4">
                <path d="M12 5v14M5 12h14" />
              </Icon>
              Add study material
            </Link>
          </section>

          <section aria-labelledby="quick-actions-heading">
            <div className="mb-4 flex items-end justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Get started
                </p>
                <h2 id="quick-actions-heading" className="mt-1 text-xl font-semibold tracking-tight text-slate-900">
                  Your workspace
                </h2>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <Link
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-lg hover:shadow-slate-900/5 focus:outline-none focus:ring-2 focus:ring-amber-400"
                href="/documents"
              >
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-amber-100 text-amber-800 transition group-hover:bg-amber-200">
                  <Icon>
                    <path d="M5 3.75h9l5 5v11.5H5z" />
                    <path d="M14 3.75v5h5M8 13h8M8 16.5h8" />
                  </Icon>
                </span>
                <h3 className="mt-5 font-semibold text-slate-900">My materials</h3>
                <p className="mt-2 min-h-10 text-sm leading-5 text-slate-500">
                  Open your course documents and keep studying.
                </p>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-amber-800">
                  Open My Materials
                  <span aria-hidden="true" className="transition group-hover:translate-x-1">→</span>
                </span>
              </Link>

              <Link
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-lg hover:shadow-slate-900/5 focus:outline-none focus:ring-2 focus:ring-amber-400"
                href="/analytics"
              >
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-100 text-indigo-700 transition group-hover:bg-indigo-200">
                  <Icon>
                    <path d="M4 19V5M4 19h16" />
                    <path d="m7 15 4-4 3 2 5-6" />
                  </Icon>
                </span>
                <h3 className="mt-5 font-semibold text-slate-900">Learning analytics</h3>
                <p className="mt-2 min-h-10 text-sm leading-5 text-slate-500">
                  Review your learning activity and progress.
                </p>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-indigo-700">
                  View Learning Analytics
                  <span aria-hidden="true" className="transition group-hover:translate-x-1">→</span>
                </span>
              </Link>

              <Link
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-lg hover:shadow-slate-900/5 focus:outline-none focus:ring-2 focus:ring-amber-400"
                href="/history"
              >
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-100 text-emerald-700 transition group-hover:bg-emerald-200">
                  <Icon>
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 7v5l3.5 2" />
                  </Icon>
                </span>
                <h3 className="mt-5 font-semibold text-slate-900">Learning history</h3>
                <p className="mt-2 min-h-10 text-sm leading-5 text-slate-500">
                  Return to your recent study sessions.
                </p>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-emerald-700">
                  View Learning History
                  <span aria-hidden="true" className="transition group-hover:translate-x-1">→</span>
                </span>
              </Link>
            </div>
          </section>

          <section className="mt-8 flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
            <div className="flex items-start gap-4">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-700">
                <Icon>
                  <path d="M12 3.5v17M3.5 12h17" />
                </Icon>
              </span>
              <div>
                <h2 className="font-semibold text-slate-900">Make your materials work harder</h2>
                <p className="mt-1 text-sm leading-5 text-slate-500">
                  Add a lecture file to start organizing your study workspace.
                </p>
              </div>
            </div>
            <Link
              className="inline-flex shrink-0 items-center justify-center rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-amber-400"
              href="/documents"
            >
              Browse materials
            </Link>
          </section>
        </div>
      </main>
    </div>
  );
}

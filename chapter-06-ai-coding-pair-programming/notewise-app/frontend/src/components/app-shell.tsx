"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/components/auth-provider";

const navigation = [
  { label: "Overview", href: "/", icon: "⌂" },
  { label: "Material Hub", href: "/materials", icon: "▤" },
  { label: "AI Quiz Player", href: "/quiz", icon: "✳" },
  { label: "Analytics", href: "/analytics", icon: "▥" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen md:flex">
      <aside className="flex w-full flex-col border-b border-slate-200 bg-white px-5 py-5 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
        <Link href="/" className="mb-8 flex items-center gap-3 text-xl font-bold tracking-tight">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-lg text-white">
            N
          </span>
          NoteWise
        </Link>
        <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Workspace
        </p>
        <nav aria-label="Main navigation" className="flex gap-2 overflow-x-auto md:flex-col">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.label}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={`flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                  isActive
                    ? "bg-indigo-50 text-brand"
                    : "text-slate-600 transition hover:bg-slate-50 hover:text-ink"
                }`}
              >
                <span aria-hidden="true" className="w-5 text-center text-lg">
                  {item.icon}
                </span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden rounded-xl bg-slate-50 p-4 md:block">
          <p className="text-sm font-semibold">Study smarter</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Keep your notes organized and turn them into useful insights.
          </p>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex min-h-[72px] items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-3 md:px-8">
          <p className="hidden text-sm text-slate-500 sm:block">Personal learning workspace</p>
          <span className="truncate text-sm font-medium text-slate-700 sm:hidden">
            NoteWise workspace
          </span>
          <div className="flex min-w-0 items-center gap-3">
            <span className="max-w-28 truncate text-xs font-medium text-slate-700 sm:max-w-64 sm:text-sm">
              {user?.email}
            </span>
            <span
              aria-hidden="true"
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-indigo-100 text-sm font-semibold uppercase text-indigo-700"
            >
              {user?.email.slice(0, 1) ?? "N"}
            </span>
            <button
              type="button"
              onClick={logout}
              className="shrink-0 rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-ink focus:outline-none focus:ring-4 focus:ring-indigo-100"
            >
              Log out
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-5 py-8 md:px-8 md:py-10">{children}</main>
      </div>
    </div>
  );
}

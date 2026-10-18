"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";

export function FeaturePlaceholder({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  const router = useRouter();
  const { user, isLoading, sessionError } = useAuth();

  useEffect(() => {
    if (!isLoading && !user && !sessionError) {
      router.replace("/login");
    }
  }, [isLoading, router, sessionError, user]);

  if (!user) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50">
        <p className="text-sm font-medium text-slate-500" role="status">
          {sessionError ?? "Loading your workspace…"}
        </p>
      </main>
    );
  }

  return (
    <AppShell>
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-semibold text-brand">NOTEWISE WORKSPACE</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-ink">{title}</h1>
        <p className="mt-3 max-w-2xl leading-7 text-slate-500">{description}</p>
        <p className="mt-8 inline-flex rounded-full bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700">
          This workspace is coming soon.
        </p>
      </section>
    </AppShell>
  );
}

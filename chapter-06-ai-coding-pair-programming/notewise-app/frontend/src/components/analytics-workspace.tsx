"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { getStoredAccessToken, useAuth } from "@/components/auth-provider";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const SESSION_EXPIRED = "Your session has expired. Please log out and sign in again.";

interface DocumentAnalytics {
  document_id: string;
  document_title: string;
  quiz_count: number;
  attempt_count: number;
  average_score_percent: number | null;
  accuracy_percent: number | null;
}

interface WeakArea {
  document_id: string;
  document_title: string;
  topic_label: string;
  wrong_count: number;
  total_count: number;
  sample_questions: string[];
}

interface AnalyticsSummary {
  total_documents: number;
  ready_documents: number;
  total_quizzes: number;
  total_attempts: number;
  average_score_percent: number | null;
  overall_accuracy_percent: number | null;
  documents: DocumentAnalytics[];
  weak_areas: WeakArea[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isPercent(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isDocumentAnalytics(value: unknown): value is DocumentAnalytics {
  return (
    isRecord(value) &&
    typeof value.document_id === "string" &&
    typeof value.document_title === "string" &&
    isCount(value.quiz_count) &&
    isCount(value.attempt_count) &&
    isPercent(value.average_score_percent) &&
    isPercent(value.accuracy_percent)
  );
}

function isWeakArea(value: unknown): value is WeakArea {
  return (
    isRecord(value) &&
    typeof value.document_id === "string" &&
    typeof value.document_title === "string" &&
    typeof value.topic_label === "string" &&
    isCount(value.wrong_count) &&
    isCount(value.total_count) &&
    Array.isArray(value.sample_questions) &&
    value.sample_questions.every((question) => typeof question === "string")
  );
}

function isAnalyticsSummary(value: unknown): value is AnalyticsSummary {
  return (
    isRecord(value) &&
    isCount(value.total_documents) &&
    isCount(value.ready_documents) &&
    isCount(value.total_quizzes) &&
    isCount(value.total_attempts) &&
    isPercent(value.average_score_percent) &&
    isPercent(value.overall_accuracy_percent) &&
    Array.isArray(value.documents) &&
    value.documents.every(isDocumentAnalytics) &&
    Array.isArray(value.weak_areas) &&
    value.weak_areas.every(isWeakArea)
  );
}

async function readPayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function getApiError(value: unknown, statusCode: number): string {
  if (statusCode === 401) {
    return SESSION_EXPIRED;
  }
  if (isRecord(value) && typeof value.detail === "string") {
    return value.detail;
  }
  return "The request could not be completed. Please try again.";
}

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value)}%`;
}

export function AnalyticsWorkspace() {
  const router = useRouter();
  const { user, isLoading: isLoadingSession, sessionError } = useAuth();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoadingSession && !user && !sessionError) {
      router.replace("/login");
    }
  }, [isLoadingSession, router, sessionError, user]);

  const loadAnalytics = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) {
      setError(SESSION_EXPIRED);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analytics/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await readPayload(response);
      if (!response.ok) {
        throw new Error(getApiError(payload, response.status));
      }
      if (!isAnalyticsSummary(payload)) {
        throw new Error("The API returned an unexpected analytics response.");
      }
      setSummary(payload);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not load your learning analytics.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      void loadAnalytics();
    }
  }, [loadAnalytics, user]);

  if (!user) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 px-5">
        <p className="text-sm font-medium text-slate-500" role={sessionError ? "alert" : "status"}>
          {sessionError ?? "Loading your workspace…"}
        </p>
      </main>
    );
  }

  if (isLoading) {
    return (
      <AppShell>
        <p className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500" role="status">
          Loading your learning analytics…
        </p>
      </AppShell>
    );
  }

  if (error || !summary) {
    return (
      <AppShell>
        <section
          className="rounded-2xl border border-rose-200 bg-white p-6 shadow-sm"
          role="alert"
        >
          <h1 className="text-lg font-semibold text-ink">Analytics could not be loaded</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {error ?? "The analytics summary is unavailable."}
          </p>
          <button
            type="button"
            onClick={() => void loadAnalytics()}
            className="mt-5 rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100"
          >
            Try again
          </button>
        </section>
      </AppShell>
    );
  }

  const metrics = [
    { label: "Total documents", value: summary.total_documents, icon: "▤", color: "bg-indigo-100 text-indigo-700" },
    { label: "Quiz attempts", value: summary.total_attempts, icon: "✳", color: "bg-amber-100 text-amber-700" },
    {
      label: "Average score",
      value: formatPercent(summary.average_score_percent),
      icon: "◎",
      color: "bg-emerald-100 text-emerald-700",
    },
  ];

  return (
    <AppShell>
      <section>
        <p className="text-sm font-semibold tracking-wide text-brand">YOUR LEARNING PROGRESS</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">Analytics</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
          See how your practice is going and find topics that could use another review.
        </p>
      </section>

      <section aria-label="Learning overview" className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => (
          <article
            key={metric.label}
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-lg hover:shadow-indigo-950/5"
          >
            <div className="flex items-start justify-between">
              <p className="text-sm font-medium text-slate-500">{metric.label}</p>
              <span
                aria-hidden="true"
                className={`grid h-11 w-11 place-items-center rounded-xl text-lg transition group-hover:scale-105 ${metric.color}`}
              >
                {metric.icon}
              </span>
            </div>
            <p className="mt-5 text-3xl font-bold tracking-tight text-ink">{metric.value}</p>
            {metric.label === "Total documents" && (
              <p className="mt-1 text-xs text-slate-400">{summary.ready_documents} ready to study</p>
            )}
          </article>
        ))}
      </section>

      {summary.total_documents === 0 && summary.total_quizzes === 0 && (
        <section className="mt-6 rounded-2xl border border-indigo-100 bg-indigo-50/70 p-6">
          <h2 className="font-semibold text-indigo-950">Your progress starts with a material</h2>
          <p className="mt-2 text-sm leading-6 text-indigo-800/80">
            Upload a document and create a quiz to see your learning insights here.
          </p>
          <Link
            href="/dashboard/materials"
            className="mt-4 inline-flex rounded-lg bg-white px-4 py-2 text-sm font-semibold text-brand transition hover:bg-indigo-50 focus:outline-none focus:ring-4 focus:ring-indigo-100"
          >
            Go to Material Hub
          </Link>
        </section>
      )}

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">Performance by document</h2>
            <p className="mt-1 text-sm text-slate-500">Accuracy across all attempts for each material.</p>
          </div>
          <p className="text-sm font-medium text-slate-500">
            Overall accuracy: {formatPercent(summary.overall_accuracy_percent)}
          </p>
        </div>

        {summary.documents.length === 0 ? (
          <p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
            Your document statistics will appear here after you add a material.
          </p>
        ) : (
          <div className="mt-6 space-y-5">
            {summary.documents.map((document) => {
              const accuracy = document.accuracy_percent;
              const barWidth = accuracy === null ? 0 : Math.min(Math.max(accuracy, 0), 100);
              return (
                <article key={document.document_id}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold text-ink">
                        {document.document_title}
                      </h3>
                      <p className="mt-1 text-xs text-slate-500">
                        {document.quiz_count} {document.quiz_count === 1 ? "quiz" : "quizzes"} ·{" "}
                        {document.attempt_count}{" "}
                        {document.attempt_count === 1 ? "attempt" : "attempts"}
                      </p>
                    </div>
                    <span className="text-sm font-semibold text-slate-700">
                      {formatPercent(accuracy)}
                    </span>
                  </div>
                  <div
                    className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-100"
                    role="progressbar"
                    aria-label={`Accuracy for ${document.document_title}`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={accuracy ?? 0}
                  >
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="mt-8">
        <div>
          <p className="text-sm font-semibold tracking-wide text-brand">PERSONALIZED PRACTICE</p>
          <h2 className="mt-2 text-xl font-bold tracking-tight text-ink">Topics to review</h2>
          <p className="mt-1 text-sm text-slate-500">
            Based on your most recent attempt for each quiz.
          </p>
        </div>

        {summary.weak_areas.length === 0 ? (
          <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5">
            <p className="font-semibold text-emerald-900">No weak areas to review right now</p>
            <p className="mt-1 text-sm leading-6 text-emerald-800/80">
              Complete a quiz to get topic-level practice suggestions.
            </p>
          </div>
        ) : (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {summary.weak_areas.map((area, index) => {
              const question = area.sample_questions[0]?.slice(0, 300) ?? "Review this topic";
              const search = new URLSearchParams({
                document: area.document_id,
                q: question,
              });
              return (
                <article
                  key={`${area.document_id}-${area.topic_label}-${index}`}
                  className="flex flex-col rounded-2xl border border-amber-100 bg-white p-5 shadow-sm transition hover:border-amber-200 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate font-semibold text-ink">{area.document_title}</h3>
                      <p className="mt-1 text-sm font-medium text-amber-700">{area.topic_label}</p>
                    </div>
                    <span className="shrink-0 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                      {area.wrong_count} wrong / {area.total_count}
                    </span>
                  </div>
                  <div className="mt-4 flex-1 space-y-2">
                    {area.sample_questions.map((sampleQuestion) => (
                      <p
                        key={sampleQuestion}
                        className="rounded-lg bg-slate-50 px-3 py-2 text-sm leading-5 text-slate-600"
                      >
                        {sampleQuestion}
                      </p>
                    ))}
                  </div>
                  <Link
                    href={`/dashboard/chat?${search.toString()}`}
                    className="mt-5 inline-flex w-fit items-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100"
                  >
                    Review now <span aria-hidden="true">→</span>
                  </Link>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </AppShell>
  );
}

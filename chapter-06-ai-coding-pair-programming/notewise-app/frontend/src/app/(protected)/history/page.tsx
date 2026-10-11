"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "../../../lib/api";

interface HistoryItem {
  id: string;
  event_type: "DOCUMENT_UPLOADED" | "SUMMARY_CREATED" | "QUESTION_ASKED" | "QUIZ_SUBMITTED";
  document_id: string | null;
  document_title: string | null;
  occurred_at: string;
  details: Record<string, unknown>;
}

interface HistoryPageData {
  items: HistoryItem[];
  page: number;
  page_size: number;
  total: number;
}

function eventLabel(eventType: HistoryItem["event_type"]): string {
  const labels: Record<HistoryItem["event_type"], string> = {
    DOCUMENT_UPLOADED: "Document uploaded",
    SUMMARY_CREATED: "Summary created",
    QUESTION_ASKED: "Document question asked",
    QUIZ_SUBMITTED: "Quiz completed",
  };
  return labels[eventType];
}

function errorMessage(body: unknown): string {
  if (body && typeof body === "object" && "error" in body) {
    const error = (body as { error?: { message?: unknown } }).error;
    if (typeof error?.message === "string") return error.message;
  }
  return "Unable to load learning history.";
}

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<HistoryPageData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void apiFetch(`/api/v1/learning-history?page=${page}&page_size=10`)
      .then(async (response) => {
        const body: unknown = await response.json();
        if (!response.ok) throw new Error(errorMessage(body));
        if (active) setData(body as HistoryPageData);
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load learning history.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, [page]);

  if (error) {
    return (
      <main className="learning-page">
        <h1>Learning history</h1>
        <p role="alert">{error}</p>
      </main>
    );
  }
  if (!data) {
    return (
      <main className="learning-page">
        <p role="status">Loading learning history…</p>
      </main>
    );
  }

  const pageCount = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <main className="learning-page analytics-page">
      <header className="analytics-header">
        <div>
          <p className="eyebrow">Your learning activity</p>
          <h1>Learning history</h1>
        </div>
        <nav aria-label="Learning">
          <a href="/analytics">Analytics</a>
          <a href="/documents">My materials</a>
        </nav>
      </header>
      {data.items.length === 0 ? (
        <p>No learning activity yet.</p>
      ) : (
        <>
          <ol className="analytics-list history-list">
            {data.items.map((item) => (
              <li className="analytics-card" key={item.id}>
                <p className="eyebrow">{eventLabel(item.event_type)}</p>
                <h2>
                  {item.document_id ? (
                    <a href={`/documents/${item.document_id}`}>
                      {item.document_title ?? "Learning document"}
                    </a>
                  ) : (
                    item.document_title ?? "Learning activity"
                  )}
                </h2>
                {typeof item.details.topic === "string" && <p>{item.details.topic}</p>}
                {typeof item.details.score === "number" && (
                  <p>{`${Number(item.details.score.toFixed(2))}%`}</p>
                )}
                <time dateTime={item.occurred_at}>
                  {new Date(item.occurred_at).toLocaleString()}
                </time>
              </li>
            ))}
          </ol>
          <nav className="history-pagination" aria-label="History pages">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </button>
            <span>
              Page {data.page} of {pageCount}
            </span>
            <button
              type="button"
              disabled={page >= pageCount}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </nav>
        </>
      )}
    </main>
  );
}

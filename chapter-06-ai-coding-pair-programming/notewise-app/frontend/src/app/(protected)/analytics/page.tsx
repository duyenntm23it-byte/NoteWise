"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "../../../lib/api";

interface Overview {
  average_score: number | null;
  document_count: number;
  completed_quiz_count: number;
}

interface Accuracy {
  accuracy: number | null;
  correct_count: number;
  answered_count: number;
  skipped_count: number;
}

interface WeakTopic {
  topic: string;
  accuracy: number | null;
  attempts: number;
  answered_count: number;
  skipped_count: number;
  sufficient_data: boolean;
  is_weak: boolean;
  reason: string | null;
}

interface Recommendation {
  id: string;
  topic: string;
  action: string;
  reason: string;
  document_id: string | null;
  chunk_id: string | null;
  page_start: number | null;
  page_end: number | null;
  created_at: string;
}

interface AnalyticsData {
  overview: Overview;
  accuracy: Accuracy;
  weakTopics: WeakTopic[];
  recommendations: Recommendation[];
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "error" in body) {
    const error = (body as { error?: { message?: unknown } }).error;
    if (typeof error?.message === "string") return error.message;
  }
  return fallback;
}

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Number(value.toFixed(2))}%`;
}

async function readJson<T>(path: string): Promise<T> {
  const response = await apiFetch(path);
  const body: unknown = await response.json();
  if (!response.ok) {
    throw new Error(errorMessage(body, "Unable to load learning analytics."));
  }
  return body as T;
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void Promise.all([
      readJson<Overview>("/api/v1/analytics/overview"),
      readJson<Accuracy>("/api/v1/analytics/accuracy"),
      readJson<{ items: WeakTopic[] }>("/api/v1/analytics/weak-topics"),
      readJson<{ items: Recommendation[] }>("/api/v1/recommendations"),
    ])
      .then(([overview, accuracy, weakTopics, recommendations]) => {
        if (active) {
          setData({
            overview,
            accuracy,
            weakTopics: weakTopics.items,
            recommendations: recommendations.items,
          });
        }
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load learning analytics.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <main className="learning-page analytics-page">
        <h1>Analytics &amp; Weak Topics</h1>
        <p role="alert">{error}</p>
      </main>
    );
  }
  if (!data) {
    return (
      <main className="learning-page analytics-page">
        <p role="status">Loading learning analytics…</p>
      </main>
    );
  }

  const weakTopics = data.weakTopics.filter((topic) => topic.is_weak);

  return (
    <main className="learning-page analytics-page">
      <header className="analytics-header">
        <div>
          <p className="eyebrow">Analytics &amp; Weak Topics</p>
          <h1>See how your learning is progressing</h1>
        </div>
        <nav aria-label="Learning">
          <a href="/documents">My materials</a>
          <a href="/history">Learning history</a>
        </nav>
      </header>

      <section aria-label="Learning overview" className="analytics-kpis">
        <article className="analytics-card">
          <h2>Average quiz score</h2>
          <strong>{formatPercent(data.overview.average_score)}</strong>
          {data.overview.average_score === null && (
            <p>No completed quizzes yet.</p>
          )}
        </article>
        <article className="analytics-card">
          <h2>Documents</h2>
          <strong>{data.overview.document_count}</strong>
        </article>
        <article className="analytics-card">
          <h2>Completed quizzes</h2>
          <strong>{data.overview.completed_quiz_count}</strong>
        </article>
      </section>

      <p className="analytics-accuracy">
        Overall answer accuracy: <strong>{formatPercent(data.accuracy.accuracy)}</strong>
        {data.accuracy.answered_count > 0 && (
          <span>
            {" "}
            ({data.accuracy.correct_count} correct of {data.accuracy.answered_count} answered;
            {" "}{data.accuracy.skipped_count} skipped)
          </span>
        )}
      </p>

      <section className="analytics-section" aria-labelledby="weak-topics-title">
        <h2 id="weak-topics-title">Weak Topics</h2>
        {weakTopics.length === 0 ? (
          <p>No weak topics identified yet.</p>
        ) : (
          <ul className="analytics-list">
            {weakTopics.map((topic) => (
              <li className="analytics-card weak-topic-card" key={topic.topic}>
                <div>
                  <h3>{topic.topic}</h3>
                  <p className="weak-topic-warning">Weak topic</p>
                </div>
                <strong>{formatPercent(topic.accuracy)}</strong>
                <p>{topic.reason}</p>
                <small>
                  {topic.attempts} submitted attempts · {topic.answered_count} answered ·{" "}
                  {topic.skipped_count} skipped
                </small>
              </li>
            ))}
          </ul>
        )}
        {data.weakTopics.some((topic) => !topic.sufficient_data) && (
          <p role="note">
            More submitted quiz attempts are needed before some topics can be assessed.
          </p>
        )}
      </section>

      <section className="analytics-section" aria-labelledby="recommendations-title">
        <h2 id="recommendations-title">Recommended Action Items</h2>
        {data.recommendations.length === 0 ? (
          <p>No study recommendations yet.</p>
        ) : (
          <ul className="analytics-list">
            {data.recommendations.map((recommendation) => {
              const href =
                recommendation.document_id && recommendation.chunk_id
                  ? `/documents/${recommendation.document_id}?chunk_id=${recommendation.chunk_id}`
                  : null;
              return (
                <li className="analytics-card" key={recommendation.id}>
                  <p className="eyebrow">{recommendation.topic}</p>
                  <h3>{recommendation.action}</h3>
                  <p>{recommendation.reason}</p>
                  {recommendation.page_start !== null && (
                    <small>
                      Page {recommendation.page_start}
                      {recommendation.page_end !== recommendation.page_start &&
                        `–${recommendation.page_end}`}
                    </small>
                  )}
                  {href ? (
                    <a className="recommendation-link" href={href}>
                      {recommendation.action}
                    </a>
                  ) : (
                    <p role="note">No relevant source passage is currently available.</p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}

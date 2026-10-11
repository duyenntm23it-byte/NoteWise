"use client";

import { useParams, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import { apiFetch } from "../../../../lib/api";

interface DocumentItem {
  id: string;
  filename: string;
  status: "PROCESSING" | "READY" | "FAILED" | "DELETING" | "DELETED";
  page_count: number | null;
}

interface CitationItem {
  chunk_id: string;
  page_number: number | null;
  section: string | null;
  excerpt: string;
}

interface SourcePassage {
  id: string;
  document_id: string;
  content: string;
  page_number: number | null;
  section: string | null;
}

interface SummaryItem {
  id: string;
  status: "QUEUED" | "PROCESSING" | "READY" | "FAILED" | "DELETED";
  content: string | null;
  failure_code: string | null;
}

interface QuestionTurn {
  question: string;
  result: QuestionResult;
}

type QuestionResult =
  | { status: "answered"; answer: string; citations: CitationItem[] }
  | {
      status: "insufficient_evidence";
      answer: null;
      citations: [];
      code: "INSUFFICIENT_EVIDENCE";
    };

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="learning-markdown">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "error" in body) {
    const error = (body as { error?: { message?: unknown } }).error;
    if (typeof error?.message === "string") return error.message;
  }
  return fallback;
}

function DocumentLearningView({
  documentId,
  chunkId,
}: {
  documentId: string;
  chunkId: string | null;
}) {
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [sourcePassage, setSourcePassage] = useState<SourcePassage | null>(null);
  const [tab, setTab] = useState<"qa" | "summary">("qa");
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<QuestionTurn[]>([]);
  const [summary, setSummary] = useState<SummaryItem | null>(null);
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingPassage, setIsLoadingPassage] = useState(false);
  const [error, setError] = useState("");
  const sourcePassageRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let active = true;
    void apiFetch(`/api/v1/documents/${documentId}`)
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(errorMessage(payload, "Unable to load document."));
        if (active) setDocument(payload as DocumentItem);
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load document.");
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [documentId]);

  useEffect(() => {
    if (!chunkId) {
      setSourcePassage(null);
      return;
    }
    let active = true;
    setIsLoadingPassage(true);
    setError("");
    void apiFetch(`/api/v1/documents/${documentId}/chunks/${chunkId}`)
      .then(async (response) => {
        const payload: unknown = await response.json();
        if (!response.ok) {
          throw new Error(errorMessage(payload, "Unable to open this source passage."));
        }
        if (active) setSourcePassage(payload as SourcePassage);
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to open this source passage.",
          );
        }
      })
      .finally(() => {
        if (active) setIsLoadingPassage(false);
      });
    return () => {
      active = false;
    };
  }, [chunkId, documentId]);

  useEffect(() => {
    if (!sourcePassage) return;
    const passageElement = sourcePassageRef.current;
    passageElement?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    passageElement?.focus();
  }, [sourcePassage]);

  async function showSummary() {
    setTab("summary");
    if (isSubmitting || summary?.status === "READY") return;
    setError("");
    setIsSubmitting(true);
    try {
      const accepted = await apiFetch(
        `/api/v1/documents/${documentId}/summaries`,
        {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID() },
        },
      );
      const acceptedBody = await accepted.json();
      if (!accepted.ok) {
        throw new Error(errorMessage(acceptedBody, "Unable to request a summary."));
      }
      let current = acceptedBody.summary as SummaryItem;
      setSummary(current);
      for (let attempt = 0; attempt < 60; attempt += 1) {
        if (current.status !== "QUEUED" && current.status !== "PROCESSING") break;
        const response = await apiFetch(`/api/v1/summaries/${current.id}`);
        const body = await response.json();
        if (!response.ok) {
          throw new Error(errorMessage(body, "Unable to load the summary."));
        }
        current = body as SummaryItem;
        setSummary(current);
        if (current.status === "QUEUED" || current.status === "PROCESSING") {
          await new Promise((resolve) => window.setTimeout(resolve, 1000));
        }
      }
      if (current.status === "QUEUED" || current.status === "PROCESSING") {
        throw new Error("Summary generation is taking longer than expected.");
      }
      if (current.status !== "READY") {
        throw new Error("The summary could not be generated. Please try again.");
      }
    } catch (summaryError) {
      setError(
        summaryError instanceof Error
          ? summaryError.message
          : "Unable to generate a summary.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || isSubmitting) return;
    const submittedQuestion = question.trim();
    setError("");
    setIsSubmitting(true);
    try {
      const response = await apiFetch(
        `/api/v1/documents/${documentId}/questions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: submittedQuestion }),
        },
      );
      const body = await response.json();
      if (!response.ok) {
        throw new Error(errorMessage(body, "Unable to answer this question."));
      }
      setTurns((previous) => [
        ...previous,
        { question: submittedQuestion, result: body as QuestionResult },
      ]);
      setQuestion("");
    } catch (questionError) {
      setError(
        questionError instanceof Error
          ? questionError.message
          : "Unable to answer this question.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <main className="learning-page"><p role="status">Loading document…</p></main>;
  if (!document) return <main className="learning-page"><p role="alert">{error || "Document not found."}</p></main>;
  if (document.status !== "READY") {
    return (
      <main className="learning-page">
        <h1>{document.filename}</h1>
        <p role="status">AI study tools are available when processing is complete. Status: {document.status}.</p>
      </main>
    );
  }

  return (
    <main className="learning-page">
      <header className="learning-header">
        <a href="/documents">My Materials</a>
        <div>
          <p className="eyebrow">Document study space</p>
          <h1>{document.filename}</h1>
          <p className="subtle">{document.page_count ?? "—"} pages · AI study assistant</p>
        </div>
      </header>
      <div className="learning-workspace">
        <section
          className="learning-source"
          aria-label="Document context"
          ref={sourcePassageRef}
          tabIndex={-1}
        >
          <h2>Document content</h2>
          {isLoadingPassage && <p role="status">Opening recommended passage…</p>}
          {sourcePassage && (
            <article
              className="recommended-source-passage"
              aria-label="Recommended source passage"
            >
              <h3>
                {sourcePassage.section ?? "Recommended passage"}
                {sourcePassage.page_number !== null &&
                  ` · Page ${sourcePassage.page_number}`}
              </h3>
              <p>{sourcePassage.content}</p>
            </article>
          )}
          <p className="subtle">
            Ask questions about this processed document. Answers are grounded in
            retrieved excerpts and include source citations.
          </p>
          <p>Page citations open the exact source excerpt used by the assistant.</p>
        </section>
        <section className="learning-assistant" aria-label="AI study assistant">
          <div role="tablist" aria-label="Study tools">
            <button
              aria-selected={tab === "qa"}
              role="tab"
              type="button"
              onClick={() => setTab("qa")}
            >
              Q&amp;A
            </button>
            <button
              aria-selected={tab === "summary"}
              role="tab"
              type="button"
              onClick={() => void showSummary()}
            >
              Summary
            </button>
          </div>
          {error && <p role="alert">{error}</p>}
          {tab === "summary" ? (
            <section role="tabpanel" aria-label="Summary">
              {isSubmitting && !summary?.content && <p role="status">Generating summary…</p>}
              {summary?.status === "READY" && summary.content && (
                <MarkdownContent content={summary.content} />
              )}
              {summary?.status === "FAILED" && (
                <p role="alert">Summary generation failed ({summary.failure_code}).</p>
              )}
              {!summary && !isSubmitting && (
                <p>Generate a summary of the main ideas and important concepts in this document.</p>
              )}
            </section>
          ) : (
            <section role="tabpanel" aria-label="Document Q&A">
              <div className="learning-conversation" aria-live="polite">
                {turns.map((turn, turnIndex) => (
                  <div className="learning-turn" key={`${turnIndex}-${turn.question}`}>
                    <p className="learning-user-question">{turn.question}</p>
                    {turn.result.status === "answered" ? (
                      <article className="learning-answer">
                        <p>{turn.result.answer}</p>
                        <div className="citation-list" aria-label="Answer citations">
                          {turn.result.citations.map((citation) => {
                            const label = [
                              citation.page_number ? `Page ${citation.page_number}` : null,
                              citation.section,
                            ].filter(Boolean).join(" · ") || "Source excerpt";
                            return (
                              <div key={citation.chunk_id}>
                                <button
                                  aria-expanded={expandedCitation === citation.chunk_id}
                                  className="citation-badge"
                                  type="button"
                                  onClick={() => setExpandedCitation(
                                    expandedCitation === citation.chunk_id
                                      ? null
                                      : citation.chunk_id,
                                  )}
                                >
                                  {label}
                                </button>
                                {expandedCitation === citation.chunk_id && (
                                  <blockquote>{citation.excerpt}</blockquote>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </article>
                    ) : (
                      <p role="status">
                        I could not find enough evidence in this document to answer
                        that question.
                      </p>
                    )}
                  </div>
                ))}
              </div>
              <form className="learning-question-form" onSubmit={submitQuestion}>
                <label htmlFor="document-question">Ask about this document</label>
                <textarea
                  id="document-question"
                  maxLength={4000}
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                />
                <button disabled={isSubmitting || !question.trim()} type="submit">
                  {isSubmitting ? "Thinking…" : "Send question"}
                </button>
              </form>
            </section>
          )}
        </section>
      </div>
    </main>
  );
}

export default function DocumentLearningPage() {
  const params = useParams<{ documentId: string }>();
  const searchParams = useSearchParams();
  return (
    <DocumentLearningView
      documentId={params.documentId}
      chunkId={searchParams.get("chunk_id")}
    />
  );
}

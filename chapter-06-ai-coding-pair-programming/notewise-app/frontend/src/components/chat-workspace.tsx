"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { getStoredAccessToken, useAuth } from "@/components/auth-provider";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DocumentItem {
  id: string;
  title: string;
  status: "processing" | "ready" | "failed";
  chunk_count: number;
}

interface Citation {
  reference: number;
  document_id: string;
  document_title: string;
  chunk_index: number;
  page_number: number | null;
  content: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
}

function isDocumentItem(value: unknown): value is DocumentItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "string" &&
    "title" in value &&
    typeof value.title === "string" &&
    "status" in value &&
    (value.status === "ready" || value.status === "processing" || value.status === "failed") &&
    "chunk_count" in value &&
    typeof value.chunk_count === "number"
  );
}

function isCitation(value: unknown): value is Citation {
  return (
    typeof value === "object" &&
    value !== null &&
    "reference" in value &&
    typeof value.reference === "number" &&
    "document_id" in value &&
    typeof value.document_id === "string" &&
    "document_title" in value &&
    typeof value.document_title === "string" &&
    "chunk_index" in value &&
    typeof value.chunk_index === "number" &&
    "page_number" in value &&
    (typeof value.page_number === "number" || value.page_number === null) &&
    "content" in value &&
    typeof value.content === "string"
  );
}

function getApiError(value: unknown): string {
  if (
    typeof value === "object" &&
    value !== null &&
    "detail" in value &&
    typeof value.detail === "string"
  ) {
    return value.detail;
  }
  return "The request could not be completed. Please try again.";
}

function isAnswer(value: unknown): value is { answer: string; citations: Citation[] } {
  return (
    typeof value === "object" &&
    value !== null &&
    "answer" in value &&
    typeof value.answer === "string" &&
    "citations" in value &&
    Array.isArray(value.citations) &&
    value.citations.every(isCitation)
  );
}

export function ChatWorkspace() {
  const router = useRouter();
  const { user, isLoading, sessionError } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const readyDocuments = useMemo(
    () => documents.filter((document) => document.status === "ready"),
    [documents],
  );

  useEffect(() => {
    if (!isLoading && !user && !sessionError) {
      router.replace("/login");
    }
  }, [isLoading, router, sessionError, user]);

  const loadDocuments = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) {
      setIsLoadingDocuments(false);
      return;
    }
    setIsLoadingDocuments(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/materials/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiError(payload));
      }
      if (!Array.isArray(payload) || !payload.every(isDocumentItem)) {
        throw new Error("The API returned an unexpected document list.");
      }
      setDocuments(payload);
      setSelectedDocumentIds((current) => {
        const readyIds = new Set(
          payload.filter(isDocumentItem).filter((document) => document.status === "ready")
            .map((document) => document.id),
        );
        const stillReady = current.filter((id) => readyIds.has(id));
        return stillReady.length > 0
          ? stillReady
          : payload
              .filter(isDocumentItem)
              .filter((document) => document.status === "ready")
              .map((document) => document.id);
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load your materials.");
    } finally {
      setIsLoadingDocuments(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      void loadDocuments();
    }
  }, [loadDocuments, user]);

  function toggleDocument(documentId: string) {
    setSelectedDocumentIds((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    );
  }

  async function sendQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isSending) {
      return;
    }
    if (selectedDocumentIds.length === 0) {
      setError("Select at least one ready document to ask a question.");
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuestion,
      citations: [],
    };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setError(null);
    setIsSending(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/rag/query`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          document_ids: selectedDocumentIds,
        }),
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiError(payload));
      }
      if (!isAnswer(payload)) {
        throw new Error("The API returned an unexpected answer.");
      }
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: payload.answer,
          citations: payload.citations,
        },
      ]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not get an answer.");
    } finally {
      setIsSending(false);
    }
  }

  if (!user) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 px-5">
        <p className="text-sm font-medium text-slate-500" role={sessionError ? "alert" : "status"}>
          {sessionError ?? "Loading your workspace…"}
        </p>
      </main>
    );
  }

  return (
    <AppShell>
      <section className="mb-7">
        <p className="text-sm font-semibold tracking-wide text-brand">GROUNDED IN YOUR LIBRARY</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          Document Q&amp;A
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
          Ask questions about your materials and explore the exact passages behind every answer.
        </p>
      </section>

      <div className="grid min-h-[620px] gap-5 lg:grid-cols-[270px_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-ink">Your sources</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">Choose which files to search.</p>
            </div>
            <button
              type="button"
              onClick={() => void loadDocuments()}
              disabled={isLoadingDocuments}
              aria-label="Refresh documents"
              className="rounded-lg px-2 py-1 text-sm font-semibold text-brand hover:bg-indigo-50 disabled:opacity-50"
            >
              ↻
            </button>
          </div>

          {isLoadingDocuments ? (
            <p className="mt-6 text-sm text-slate-500" role="status">
              Loading your materials…
            </p>
          ) : readyDocuments.length === 0 ? (
            <div className="mt-6 rounded-xl bg-slate-50 p-4">
              <p className="text-sm font-medium text-ink">No ready documents yet</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Upload a PDF or TXT file to start asking questions.
              </p>
            </div>
          ) : (
            <>
              <div className="mt-5 space-y-2">
                {readyDocuments.map((document) => (
                  <label
                    key={document.id}
                    className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                      selectedDocumentIds.includes(document.id)
                        ? "border-indigo-200 bg-indigo-50/70"
                        : "border-slate-100 hover:border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedDocumentIds.includes(document.id)}
                      onChange={() => toggleDocument(document.id)}
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-ink">
                        {document.title}
                      </span>
                      <span className="mt-1 block text-xs text-slate-500">
                        {document.chunk_count} {document.chunk_count === 1 ? "passage" : "passages"}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-400">
                {selectedDocumentIds.length} selected
              </p>
            </>
          )}
        </aside>

        <section className="flex min-h-[620px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <header className="flex items-center gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-50 text-lg text-brand">
              ✳
            </span>
            <div>
              <h2 className="text-sm font-semibold text-ink">NoteWise assistant</h2>
              <p className="mt-0.5 text-xs text-slate-500">Answers grounded in selected sources</p>
            </div>
            <span className="ml-auto inline-flex items-center gap-2 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Ready
            </span>
          </header>

          <div
            className="flex-1 space-y-6 overflow-y-auto bg-slate-50/60 px-4 py-6 sm:px-7"
            aria-live="polite"
            aria-label="Conversation"
          >
            {messages.length === 0 ? (
              <div className="grid min-h-[380px] place-items-center">
                <div className="max-w-sm text-center">
                  <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-indigo-100 text-2xl text-brand">
                    ✦
                  </span>
                  <h3 className="mt-5 text-lg font-semibold text-ink">What would you like to learn?</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Select one or more sources, then ask a question about their content.
                  </p>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <article
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {message.role === "assistant" && (
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-indigo-100 text-sm text-brand">
                      ✳
                    </span>
                  )}
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 sm:max-w-[78%] ${
                      message.role === "user"
                        ? "rounded-br-md bg-brand text-white"
                        : "rounded-bl-md border border-slate-100 bg-white text-slate-700 shadow-sm"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    {message.role === "assistant" && message.citations.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                        {message.citations.map((citation) => (
                          <button
                            key={`${citation.document_id}-${citation.chunk_index}`}
                            type="button"
                            onClick={() => setActiveCitation(citation)}
                            className="inline-flex max-w-full items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100 focus:outline-none focus:ring-4 focus:ring-indigo-100"
                            aria-label={`View citation [${citation.reference}] from ${citation.document_title}, chunk ${citation.chunk_index + 1}`}
                          >
                            <span>[{citation.reference}]</span>
                            <span className="truncate">{citation.document_title}</span>
                            <span>· §{citation.chunk_index + 1}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {message.role === "user" && (
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-200 text-xs font-semibold uppercase text-slate-600">
                      {user.email.slice(0, 1)}
                    </span>
                  )}
                </article>
              ))
            )}
            {isSending && (
              <div className="flex items-center gap-3" role="status">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-100 text-sm text-brand">
                  ✳
                </span>
                <p className="rounded-2xl rounded-bl-md border border-slate-100 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                  Searching your sources…
                </p>
              </div>
            )}
          </div>

          {error && (
            <p role="alert" className="mx-5 mt-3 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </p>
          )}
          <form onSubmit={sendQuestion} className="border-t border-slate-100 bg-white p-4 sm:p-5">
            <label htmlFor="chat-question" className="sr-only">
              Ask a question about your selected documents
            </label>
            <div className="flex items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-2 pl-4 transition focus-within:border-indigo-300 focus-within:ring-4 focus-within:ring-indigo-50">
              <textarea
                id="chat-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                rows={1}
                maxLength={4000}
                placeholder="Ask anything about your documents…"
                className="max-h-32 min-h-10 flex-1 resize-y bg-transparent py-2 text-sm text-ink outline-none placeholder:text-slate-400"
              />
              <button
                type="submit"
                disabled={isSending || question.trim().length === 0}
                className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand text-lg text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Send question"
              >
                ↑
              </button>
            </div>
            <p className="mt-2 text-center text-xs text-slate-400">
              Answers are generated from your selected materials. Click a source badge to inspect it.
            </p>
          </form>
        </section>
      </div>

      {activeCitation && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-slate-950/30"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setActiveCitation(null);
            }
          }}
        >
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="citation-title"
            className="flex h-full w-full max-w-lg flex-col bg-white shadow-2xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand">
                  Source excerpt
                </p>
                <h2 id="citation-title" className="mt-1 truncate text-lg font-semibold text-ink">
                  {activeCitation.document_title}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Chunk {activeCitation.chunk_index + 1}
                  {activeCitation.page_number !== null && ` · Page ${activeCitation.page_number}`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveCitation(null)}
                className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100 hover:text-ink focus:outline-none focus:ring-4 focus:ring-indigo-100"
                aria-label="Close citation"
              >
                ✕
              </button>
            </header>
            <div className="flex-1 overflow-y-auto p-6">
              <p className="whitespace-pre-wrap rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 text-sm leading-7 text-slate-700">
                {activeCitation.content}
              </p>
            </div>
          </aside>
        </div>
      )}
    </AppShell>
  );
}

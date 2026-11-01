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

interface QuizQuestion {
  id: string;
  position: number;
  question_text: string;
  options: string[];
}

interface QuizDetail {
  id: string;
  title: string;
  total_questions: number;
  questions: QuizQuestion[];
}

interface QuizSummary {
  id: string;
  title: string;
  total_questions: number;
  created_at: string;
  latest_score: number | null;
}

interface QuestionResult extends QuizQuestion {
  question_id: string;
  position: number;
  question_text: string;
  options: string[];
  selected_index: number | null;
  correct_answer: number;
  is_correct: boolean;
  explanation: string;
  source_document_title: string;
  source_chunk_index: number | null;
  source_page_number: number | null;
}

interface QuizAttempt {
  score: number;
  total: number;
  results: QuestionResult[];
}

type QuizView = "library" | "play" | "result";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDocumentItem(value: unknown): value is DocumentItem {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    (value.status === "ready" || value.status === "processing" || value.status === "failed") &&
    typeof value.chunk_count === "number"
  );
}

function isQuizQuestion(value: unknown): value is QuizQuestion {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.position === "number" &&
    typeof value.question_text === "string" &&
    Array.isArray(value.options) &&
    value.options.length === 4 &&
    value.options.every((option) => typeof option === "string")
  );
}

function isQuizDetail(value: unknown): value is QuizDetail {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.total_questions === "number" &&
    Array.isArray(value.questions) &&
    value.questions.every(isQuizQuestion)
  );
}

function isQuizSummary(value: unknown): value is QuizSummary {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.total_questions === "number" &&
    typeof value.created_at === "string" &&
    (typeof value.latest_score === "number" || value.latest_score === null)
  );
}

function isQuestionResult(value: unknown): value is QuestionResult {
  return (
    isRecord(value) &&
    typeof value.question_id === "string" &&
    typeof value.position === "number" &&
    typeof value.question_text === "string" &&
    Array.isArray(value.options) &&
    value.options.length === 4 &&
    value.options.every((option) => typeof option === "string") &&
    (value.selected_index === null || typeof value.selected_index === "number") &&
    typeof value.correct_answer === "number" &&
    typeof value.is_correct === "boolean" &&
    typeof value.explanation === "string" &&
    typeof value.source_document_title === "string" &&
    (typeof value.source_chunk_index === "number" || value.source_chunk_index === null) &&
    (typeof value.source_page_number === "number" || value.source_page_number === null)
  );
}

function isQuizAttempt(value: unknown): value is QuizAttempt {
  return (
    isRecord(value) &&
    typeof value.score === "number" &&
    typeof value.total === "number" &&
    Array.isArray(value.results) &&
    value.results.every(isQuestionResult)
  );
}

async function readPayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function getApiError(value: unknown, statusCode?: number): string {
  if (statusCode === 429) {
    return "Gemini is receiving too many requests. Please wait a moment and try again.";
  }
    if (statusCode === 401) {
    return "Your session has expired. Please log out and sign in again.";
  }
  if (statusCode === 503) {
    return "AI quiz generation is temporarily unavailable. Please try again later.";
  }
  if (statusCode === 502) {
    return "The AI could not create a valid quiz this time. Please try again.";
  }
  if (isRecord(value) && typeof value.detail === "string") {
    return value.detail;
  }
  return "The request could not be completed. Please try again.";
}

export function QuizWorkspace() {
  const router = useRouter();
  const { user, isLoading, sessionError } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [quizzes, setQuizzes] = useState<QuizSummary[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [numQuestions, setNumQuestions] = useState<5 | 10>(5);
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [view, setView] = useState<QuizView>("library");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoadingLibrary, setIsLoadingLibrary] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isOpeningQuiz, setIsOpeningQuiz] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeneratorOpen, setIsGeneratorOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readyDocuments = useMemo(
    () => documents.filter((document) => document.status === "ready"),
    [documents],
  );
  const currentQuestion = quiz?.questions[currentIndex];

  useEffect(() => {
    if (!isLoading && !user && !sessionError) {
      router.replace("/login");
    }
  }, [isLoading, router, sessionError, user]);

  const loadLibrary = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) {
      setIsLoadingLibrary(false);
      return;
    }
    setIsLoadingLibrary(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [documentsResponse, quizzesResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/materials/`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/quizzes/`, { headers }),
      ]);
      const [documentsPayload, quizzesPayload] = await Promise.all([
        readPayload(documentsResponse),
        readPayload(quizzesResponse),
      ]);
      if (!documentsResponse.ok) {
        throw new Error(getApiError(documentsPayload, documentsResponse.status));
      }
      if (!quizzesResponse.ok) {
        throw new Error(getApiError(quizzesPayload, quizzesResponse.status));
      }
      if (
        !Array.isArray(documentsPayload) ||
        !documentsPayload.every(isDocumentItem) ||
        !Array.isArray(quizzesPayload) ||
        !quizzesPayload.every(isQuizSummary)
      ) {
        throw new Error("The API returned an unexpected quiz library response.");
      }
      setDocuments(documentsPayload);
      setQuizzes(quizzesPayload);
      setSelectedDocumentId((current) => {
        if (documentsPayload.some((document) => document.id === current && document.status === "ready")) {
          return current;
        }
        return documentsPayload.find((document) => document.status === "ready")?.id ?? "";
      });
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load your quiz library.");
    } finally {
      setIsLoadingLibrary(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      void loadLibrary();
    }
  }, [loadLibrary, user]);

  async function openQuiz(quizId: string) {
    const token = getStoredAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    setIsOpeningQuiz(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/quizzes/${quizId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await readPayload(response);
      if (!response.ok) {
        throw new Error(getApiError(payload, response.status));
      }
      if (!isQuizDetail(payload)) {
        throw new Error("The API returned an unexpected quiz.");
      }
      setQuiz(payload);
      setAnswers({});
      setAttempt(null);
      setCurrentIndex(0);
      setView("play");
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "Could not open this quiz.");
    } finally {
      setIsOpeningQuiz(false);
    }
  }

  async function generateQuiz(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getStoredAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    if (!selectedDocumentId) {
      setError("Choose a ready document before creating a quiz.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/quizzes/generate`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_id: selectedDocumentId,
          num_questions: numQuestions,
        }),
      });
      const payload = await readPayload(response);
      if (!response.ok) {
        throw new Error(getApiError(payload, response.status));
      }
      if (!isQuizDetail(payload)) {
        throw new Error("The API returned an unexpected quiz.");
      }
      setQuiz(payload);
      setAnswers({});
      setAttempt(null);
      setCurrentIndex(0);
      setIsGeneratorOpen(false);
      setView("play");
      void loadLibrary();
    } catch (generateError) {
      setError(
        generateError instanceof Error
          ? generateError.message
          : "Could not generate your quiz. Please try again.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function submitQuiz() {
    const token = getStoredAccessToken();
    if (!token || !quiz || isSubmitting) {
      if (!token) {
        router.replace("/login");
      }
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/quizzes/${quiz.id}/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          answers: quiz.questions.map((question) => ({
            question_id: question.id,
            selected_index: answers[question.id] ?? null,
          })),
        }),
      });
      const payload = await readPayload(response);
      if (!response.ok) {
        throw new Error(getApiError(payload, response.status));
      }
      if (!isQuizAttempt(payload)) {
        throw new Error("The API returned an unexpected quiz result.");
      }
      setAttempt(payload);
      setView("result");
      void loadLibrary();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Could not submit this quiz.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function retryQuiz() {
    if (!quiz) {
      return;
    }
    setAnswers({});
    setAttempt(null);
    setCurrentIndex(0);
    setError(null);
    setView("play");
  }

  function startNewQuiz() {
    setView("library");
    setQuiz(null);
    setAttempt(null);
    setError(null);
    setIsGeneratorOpen(true);
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
      <section className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold tracking-wide text-brand">PRACTICE WITH YOUR MATERIALS</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            AI Quiz Player
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
            Turn your notes into focused practice and review explanations grounded in your sources.
          </p>
        </div>
        {view === "library" && (
          <button
            type="button"
            onClick={() => {
              setError(null);
              setIsGeneratorOpen(true);
            }}
            disabled={readyDocuments.length === 0 || isLoadingLibrary}
            className="inline-flex w-fit items-center gap-2 rounded-xl bg-brand px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span aria-hidden="true">✦</span>
            Tạo Quiz bằng AI
          </button>
        )}
      </section>

      {error && (
        <p role="alert" className="mb-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </p>
      )}

      {view === "library" && (
        <section>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Your quizzes</h2>
              <p className="mt-1 text-sm text-slate-500">Continue a quiz or review your latest scores.</p>
            </div>
            <button
              type="button"
              onClick={() => void loadLibrary()}
              disabled={isLoadingLibrary}
              className="rounded-lg px-3 py-2 text-sm font-semibold text-brand transition hover:bg-indigo-50 disabled:opacity-50"
            >
              Refresh
            </button>
          </div>
          {isLoadingLibrary ? (
            <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
              Loading your quiz library…
            </div>
          ) : quizzes.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
              <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-indigo-50 text-2xl text-brand">
                ✦
              </span>
              <h2 className="mt-5 font-semibold text-ink">No quizzes yet</h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
                Create a quiz from one of your ready documents to start practicing.
              </p>
              {readyDocuments.length > 0 && (
                <button
                  type="button"
                  onClick={() => setIsGeneratorOpen(true)}
                  className="mt-5 rounded-xl bg-brand px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100"
                >
                  Tạo Quiz bằng AI
                </button>
              )}
            </div>
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2">
              {quizzes.map((item) => (
                <li key={item.id}>
                  <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-200 hover:shadow-md">
                    <div className="flex items-start justify-between gap-3">
                      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-indigo-50 text-lg text-brand">
                        ✳
                      </span>
                      {item.latest_score !== null && (
                        <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                          Latest: {item.latest_score}/{item.total_questions}
                        </span>
                      )}
                    </div>
                    <h3 className="mt-4 line-clamp-2 font-semibold text-ink">{item.title}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {item.total_questions} questions ·{" "}
                      {new Date(item.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </p>
                    <button
                      type="button"
                      onClick={() => void openQuiz(item.id)}
                      disabled={isOpeningQuiz}
                      className="mt-5 inline-flex w-fit items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-brand transition hover:bg-indigo-50 focus:outline-none focus:ring-4 focus:ring-indigo-100 disabled:opacity-50"
                    >
                      {isOpeningQuiz ? "Opening…" : "Start quiz"}
                      <span aria-hidden="true">→</span>
                    </button>
                  </article>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {view === "play" && quiz && currentQuestion && (
        <section className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <header className="border-b border-slate-100 px-5 py-5 sm:px-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-brand">Quiz in progress</p>
                <h2 className="mt-1 text-lg font-semibold text-ink">{quiz.title}</h2>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
                {currentIndex + 1} of {quiz.total_questions}
              </span>
            </div>
            <div
              className="mt-5 h-2 overflow-hidden rounded-full bg-indigo-100"
              role="progressbar"
              aria-label="Quiz progress"
              aria-valuemin={0}
              aria-valuemax={quiz.total_questions}
              aria-valuenow={currentIndex + 1}
            >
              <div
                className="h-full rounded-full bg-brand transition-all duration-300"
                style={{ width: `${((currentIndex + 1) / quiz.total_questions) * 100}%` }}
              />
            </div>
            <div className="mt-4 flex flex-wrap gap-2" aria-label="Question stepper">
              {quiz.questions.map((question, index) => (
                <button
                  key={question.id}
                  type="button"
                  onClick={() => setCurrentIndex(index)}
                  aria-label={`Go to question ${index + 1}`}
                  aria-current={index === currentIndex ? "step" : undefined}
                  className={`grid h-8 w-8 place-items-center rounded-full text-xs font-semibold transition focus:outline-none focus:ring-4 focus:ring-indigo-100 ${
                    index === currentIndex
                      ? "bg-brand text-white"
                      : answers[question.id] !== undefined
                        ? "bg-indigo-100 text-brand hover:bg-indigo-200"
                        : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}
                >
                  {index + 1}
                </button>
              ))}
            </div>
          </header>

          <div className="px-5 py-7 sm:px-8 sm:py-9">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Question {currentIndex + 1}
            </p>
            <h3 className="mt-3 text-xl font-semibold leading-8 text-ink sm:text-2xl">
              {currentQuestion.question_text}
            </h3>
            <fieldset className="mt-7 space-y-3">
              <legend className="sr-only">Choose one answer</legend>
              {currentQuestion.options.map((option, index) => {
                const isSelected = answers[currentQuestion.id] === index;
                return (
                  <label
                    key={`${currentQuestion.id}-${index}`}
                    className={`flex cursor-pointer items-start gap-4 rounded-xl border p-4 transition focus-within:ring-4 focus-within:ring-indigo-100 ${
                      isSelected
                        ? "border-indigo-300 bg-indigo-50 shadow-sm"
                        : "border-slate-200 bg-white hover:border-indigo-200 hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`question-${currentQuestion.id}`}
                      value={index}
                      checked={isSelected}
                      onChange={() =>
                        setAnswers((current) => ({ ...current, [currentQuestion.id]: index }))
                      }
                      className="sr-only"
                    />
                    <span
                      aria-hidden="true"
                      className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg text-sm font-semibold ${
                        isSelected ? "bg-brand text-white" : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {"ABCD"[index]}
                    </span>
                    <span className="pt-1 text-sm leading-6 text-slate-700">{option}</span>
                  </label>
                );
              })}
            </fieldset>
          </div>

          <footer className="flex items-center justify-between gap-3 border-t border-slate-100 bg-slate-50/70 px-5 py-4 sm:px-8">
            <button
              type="button"
              onClick={() => setCurrentIndex((index) => Math.max(0, index - 1))}
              disabled={currentIndex === 0 || isSubmitting}
              className="rounded-lg px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← Previous
            </button>
            {currentIndex < quiz.total_questions - 1 ? (
              <button
                type="button"
                onClick={() => setCurrentIndex((index) => Math.min(quiz.total_questions - 1, index + 1))}
                className="rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100"
              >
                Next →
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void submitQuiz()}
                disabled={isSubmitting}
                className="rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100 disabled:opacity-50"
              >
                {isSubmitting ? "Submitting…" : "Submit quiz"}
              </button>
            )}
          </footer>
        </section>
      )}

      {view === "result" && quiz && attempt && (
        <section className="mx-auto max-w-3xl">
          <div className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 to-white p-6 text-center shadow-sm sm:p-9">
            <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-white text-2xl text-brand shadow-sm">
              {attempt.score === attempt.total ? "✦" : "✓"}
            </span>
            <p className="mt-4 text-sm font-semibold uppercase tracking-wide text-brand">Quiz complete</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-ink">
              {attempt.score} <span className="text-slate-400">/ {attempt.total}</span>
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              {attempt.score === attempt.total
                ? "Perfect score. Excellent work!"
                : "Review the explanations below to strengthen your understanding."}
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <button
                type="button"
                onClick={retryQuiz}
                className="rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100"
              >
                Retry quiz
              </button>
              <button
                type="button"
                onClick={startNewQuiz}
                className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-indigo-100"
              >
                Create a new quiz
              </button>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {attempt.results.map((result, index) => (
              <article
                key={result.question_id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
              >
                <div className="flex items-start gap-3">
                  <span
                    className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold ${
                      result.is_correct
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-rose-100 text-rose-700"
                    }`}
                  >
                    {result.is_correct ? "✓" : "×"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Question {index + 1} · {result.is_correct ? "Correct" : "Review"}
                    </p>
                    <h3 className="mt-1 font-semibold leading-6 text-ink">{result.question_text}</h3>
                  </div>
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {result.options.map((option, optionIndex) => {
                    const isCorrect = optionIndex === result.correct_answer;
                    const isSelected = optionIndex === result.selected_index;
                    return (
                      <p
                        key={`${result.question_id}-${optionIndex}`}
                        className={`rounded-lg border px-3 py-2 text-sm ${
                          isCorrect
                            ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                            : isSelected
                              ? "border-rose-200 bg-rose-50 text-rose-800"
                              : "border-slate-100 bg-slate-50 text-slate-600"
                        }`}
                      >
                        <span className="mr-2 font-semibold">{"ABCD"[optionIndex]}.</span>
                        {option}
                        {isCorrect && <span className="ml-2 text-xs font-semibold">Correct answer</span>}
                        {isSelected && !isCorrect && (
                          <span className="ml-2 text-xs font-semibold">Your answer</span>
                        )}
                        {isSelected && isCorrect && (
                          <span className="ml-2 text-xs font-semibold">Your answer</span>
                        )}
                      </p>
                    );
                  })}
                </div>
                <div className="mt-4 rounded-xl bg-indigo-50/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
                    Explanation
                  </p>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{result.explanation}</p>
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Source: <span className="font-medium text-slate-700">{result.source_document_title}</span>
                  {result.source_page_number !== null && ` · Page ${result.source_page_number}`}
                  {result.source_page_number === null &&
                    result.source_chunk_index !== null &&
                    ` · Passage ${result.source_chunk_index + 1}`}
                  {result.selected_index === null && (
                    <span className="ml-2 font-medium text-rose-600">Not answered</span>
                  )}
                </p>
              </article>
            ))}
          </div>
        </section>
      )}

      {isGeneratorOpen && view === "library" && (
        <div
          className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/30 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isGenerating) {
              setIsGeneratorOpen(false);
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="quiz-generator-title"
            className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl sm:p-8"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-brand">AI study tools</p>
                <h2 id="quiz-generator-title" className="mt-1 text-xl font-bold text-ink">
                  Create a quiz
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Choose a ready document and let NoteWise build a source-grounded quiz.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsGeneratorOpen(false)}
                disabled={isGenerating}
                aria-label="Close quiz generator"
                className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100 disabled:opacity-50"
              >
                ✕
              </button>
            </div>

            <form onSubmit={generateQuiz} className="mt-6 space-y-5">
              <div>
                <label htmlFor="quiz-document" className="mb-2 block text-sm font-semibold text-ink">
                  Source document
                </label>
                <select
                  id="quiz-document"
                  value={selectedDocumentId}
                  onChange={(event) => setSelectedDocumentId(event.target.value)}
                  disabled={isGenerating || readyDocuments.length === 0}
                  required
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-indigo-300 focus:ring-4 focus:ring-indigo-50 disabled:bg-slate-50"
                >
                  {readyDocuments.length === 0 ? (
                    <option value="">No ready documents available</option>
                  ) : (
                    readyDocuments.map((document) => (
                      <option key={document.id} value={document.id}>
                        {document.title}
                      </option>
                    ))
                  )}
                </select>
                {readyDocuments.length === 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    Upload a document in Material Hub and wait for processing to finish.
                  </p>
                )}
              </div>

              <fieldset>
                <legend className="mb-2 text-sm font-semibold text-ink">Number of questions</legend>
                <div className="grid grid-cols-2 gap-3">
                  {([5, 10] as const).map((count) => (
                    <label
                      key={count}
                      className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition ${
                        numQuestions === count
                          ? "border-indigo-200 bg-indigo-50"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="quiz-question-count"
                        value={count}
                        checked={numQuestions === count}
                        onChange={() => setNumQuestions(count)}
                        className="h-4 w-4 accent-indigo-600"
                      />
                      <span className="text-sm font-medium text-ink">{count} questions</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <p className="rounded-xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
                Each quiz uses one AI generation request. Questions are generated from the selected
                document and answers are revealed after submission.
              </p>
              <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setIsGeneratorOpen(false)}
                  disabled={isGenerating}
                  className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating || !selectedDocumentId}
                  className="rounded-xl bg-brand px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isGenerating ? "Generating quiz…" : "Tạo Quiz bằng AI"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {isOpeningQuiz && (
        <div className="sr-only" role="status">
          Opening quiz…
        </div>
      )}
    </AppShell>
  );
}

"use client";

import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { apiFetch } from "../../../../../lib/api";

type QuestionType = "multiple_choice" | "true_false" | "fill_blank";
type QuizStatus = "QUEUED" | "PROCESSING" | "READY" | "FAILED" | "DELETED";

interface Citation {
  chunk_id: string;
  page_number: number | null;
  section: string | null;
  excerpt: string;
}

interface QuizQuestion {
  id: string;
  position: number;
  question: string;
  question_type: QuestionType;
  options: string[];
  citation: Citation;
}

interface Quiz {
  id: string;
  title: string;
  status: QuizStatus;
  failure_code: string | null;
  questions: QuizQuestion[];
}

interface QuizAttempt {
  id: string;
  quiz_id: string;
  status: "IN_PROGRESS" | "SUBMITTED";
  questions: QuizQuestion[];
  result: QuizResult | null;
}

interface QuizFeedback {
  question_id: string;
  is_correct: boolean;
  explanation?: string | null;
  citation?: Citation | null;
  submitted_answer?: string | number | null;
  correct_answer?: string | number | string[] | null;
}

interface QuizResult {
  attempt_id: string;
  score: number;
  correct_count: number;
  answered_count: number;
  skipped_count: number;
  submitted_at: string;
  feedback: QuizFeedback[];
}

const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
  { value: "multiple_choice", label: "Multiple choice" },
  { value: "true_false", label: "True / False" },
  { value: "fill_blank", label: "Fill in the blank" },
];
const DIFFICULTIES = ["easy", "medium", "hard"] as const;

function responseMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "error" in body) {
    const error = (body as { error?: { message?: unknown } }).error;
    if (typeof error?.message === "string") return error.message;
  }
  return fallback;
}

async function readBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function citationLabel(citation: Citation): string {
  if (citation.page_number !== null) return `Page ${citation.page_number}`;
  return citation.section ?? "Source excerpt";
}

export default function QuizPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const [questionCount, setQuestionCount] = useState(10);
  const [questionTypes, setQuestionTypes] = useState<QuestionType[]>([
    "multiple_choice",
  ]);
  const [difficulty, setDifficulty] = useState<(typeof DIFFICULTIES)[number]>(
    "medium",
  );
  const [topic, setTopic] = useState("");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [questionIndex, setQuestionIndex] = useState(0);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSubmitConfirmation, setShowSubmitConfirmation] = useState(false);
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null);
  const [error, setError] = useState("");

  const startAttempt = useCallback(async (readyQuiz: Quiz) => {
    const response = await apiFetch(
      `/api/v1/quizzes/${readyQuiz.id}/attempts`,
      { method: "POST" },
    );
    const body = await readBody(response);
    if (!response.ok) {
      throw new Error(responseMessage(body, "Unable to start this quiz."));
    }
    const createdAttempt = body as QuizAttempt;
    if (createdAttempt.status === "SUBMITTED" && createdAttempt.result) {
      setResult(createdAttempt.result);
    }
    setQuiz(readyQuiz);
    setAttempt(createdAttempt);
    sessionStorage.setItem(
      `notewise.quiz.${documentId}`,
      JSON.stringify({ quizId: readyQuiz.id, attemptId: createdAttempt.id }),
    );
  }, [documentId]);

  const createQuiz = useCallback(async () => {
    setError("");
    if (questionCount < 5 || questionCount > 20) {
      setError("Choose between 5 and 20 questions.");
      return;
    }
    if (questionTypes.length === 0) {
      setError("Choose at least one question type.");
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await apiFetch(
        `/api/v1/documents/${documentId}/quizzes`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question_count: questionCount,
            question_types: questionTypes,
            difficulty,
            ...(topic.trim() ? { topic: topic.trim() } : {}),
          }),
        },
      );
      const body = await readBody(response);
      if (!response.ok) {
        throw new Error(responseMessage(body, "Unable to create this quiz."));
      }
      const accepted = body as { quiz_id: string; status: QuizStatus };
      let current: Quiz | null = null;
      for (let poll = 0; poll < 60; poll += 1) {
        const quizResponse = await apiFetch(`/api/v1/quizzes/${accepted.quiz_id}`);
        const quizBody = await readBody(quizResponse);
        if (!quizResponse.ok) {
          throw new Error(responseMessage(quizBody, "Unable to load this quiz."));
        }
        current = quizBody as Quiz;
        setQuiz(current);
        if (current.status !== "QUEUED" && current.status !== "PROCESSING") break;
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
      }
      if (!current || current.status === "QUEUED" || current.status === "PROCESSING") {
        throw new Error("Quiz generation is taking longer than expected.");
      }
      if (current.status !== "READY") {
        throw new Error(
          current.failure_code
            ? `Quiz generation failed (${current.failure_code}).`
            : "Quiz generation failed. Please try again.",
        );
      }
      await startAttempt(current);
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : "Unable to create this quiz.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [
    difficulty,
    documentId,
    questionCount,
    questionTypes,
    startAttempt,
    topic,
  ]);

  useEffect(() => {
    const stored = sessionStorage.getItem(`notewise.quiz.${documentId}`);
    if (!stored) return;
    let state: { quizId: string; attemptId: string };
    try {
      state = JSON.parse(stored) as { quizId: string; attemptId: string };
    } catch {
      sessionStorage.removeItem(`notewise.quiz.${documentId}`);
      setError("The saved quiz session was invalid. Please start a new quiz.");
      return;
    }
    if (!state.quizId || !state.attemptId) {
      sessionStorage.removeItem(`notewise.quiz.${documentId}`);
      setError("The saved quiz session was incomplete. Please start a new quiz.");
      return;
    }
    let active = true;
    void Promise.all([
      apiFetch(`/api/v1/quizzes/${state.quizId}`),
      apiFetch(`/api/v1/quiz-attempts/${state.attemptId}`),
    ])
      .then(async ([quizResponse, attemptResponse]) => {
        const [quizBody, attemptBody] = await Promise.all([
          readBody(quizResponse),
          readBody(attemptResponse),
        ]);
        if (!quizResponse.ok || !attemptResponse.ok) {
          throw new Error(
            responseMessage(
              !quizResponse.ok ? quizBody : attemptBody,
              "Unable to restore this quiz attempt.",
            ),
          );
        }
        if (!active) return;
        const restoredQuiz = quizBody as Quiz;
        const restoredAttempt = attemptBody as QuizAttempt;
        const savedAnswers = sessionStorage.getItem(
          `notewise.quiz.answers.${restoredAttempt.id}`,
        );
        if (savedAnswers) {
          const parsed = JSON.parse(savedAnswers) as Record<string, unknown>;
          const questionIds = new Set(
            restoredAttempt.questions.map((question) => question.id),
          );
          if (
            Object.entries(parsed).some(
              ([questionId, answer]) =>
                !questionIds.has(questionId) || typeof answer !== "string",
            )
          ) {
            throw new Error("The saved answers were invalid and could not be restored.");
          }
          setAnswers(parsed as Record<string, string>);
        }
        setQuiz(restoredQuiz);
        setAttempt(restoredAttempt);
        if (restoredAttempt.result) setResult(restoredAttempt.result);
      })
      .catch((restoreError: unknown) => {
        if (active) {
          sessionStorage.removeItem(`notewise.quiz.${documentId}`);
          setError(
            restoreError instanceof Error
              ? restoreError.message
              : "Unable to restore this quiz attempt.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, [documentId]);

  useEffect(() => {
    if (!attempt || attempt.status !== "IN_PROGRESS" || result) return;
    sessionStorage.setItem(
      `notewise.quiz.answers.${attempt.id}`,
      JSON.stringify(answers),
    );
  }, [answers, attempt, result]);

  async function submitAnswers() {
    if (!attempt || isSubmitting || result) return;
    setError("");
    setIsSubmitting(true);
    try {
      const response = await apiFetch(
        `/api/v1/quiz-attempts/${attempt.id}/submit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            answers: Object.entries(answers).map(([question_id, answer]) => ({
              question_id,
              answer,
            })),
          }),
        },
      );
      const body = await readBody(response);
      if (!response.ok) {
        throw new Error(responseMessage(body, "Unable to submit this quiz."));
      }
      setResult(body as QuizResult);
      sessionStorage.removeItem(`notewise.quiz.answers.${attempt.id}`);
      setShowSubmitConfirmation(false);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Unable to submit this quiz.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function toggleQuestionType(type: QuestionType) {
    setQuestionTypes((selected) =>
      selected.includes(type)
        ? selected.filter((item) => item !== type)
        : [...selected, type],
    );
  }

  if (!attempt || !quiz) {
    return (
      <main className="quiz-page">
        <header className="quiz-header">
          <a href="/documents">My Materials</a>
          <div>
            <p className="eyebrow">Screen 4 · AI Quiz</p>
            <h1>Set up your quiz</h1>
            <p className="subtle">Create a source-grounded practice quiz.</p>
          </div>
        </header>
        {error && <p className="quiz-error" role="alert">{error}</p>}
        <form
          className="quiz-setup-card"
          onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            void createQuiz();
          }}
        >
          <label>
            Number of questions
            <input
              aria-label="Number of questions"
              max={20}
              min={5}
              type="range"
              value={questionCount}
              onChange={(event) => setQuestionCount(Number(event.target.value))}
            />
            <output>{questionCount} questions</output>
          </label>
          <fieldset>
            <legend>Question types</legend>
            {QUESTION_TYPES.map(({ value, label }) => (
              <label key={value}>
                <input
                  checked={questionTypes.includes(value)}
                  type="checkbox"
                  onChange={() => toggleQuestionType(value)}
                />
                {label}
              </label>
            ))}
          </fieldset>
          <label>
            Difficulty
            <select
              value={difficulty}
              onChange={(event) =>
                setDifficulty(event.target.value as (typeof DIFFICULTIES)[number])
              }
            >
              {DIFFICULTIES.map((level) => (
                <option key={level} value={level}>
                  {level[0].toUpperCase() + level.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Optional topic
            <input
              maxLength={200}
              type="text"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
            />
          </label>
          <button className="quiz-primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Generating quiz…" : "Create quiz"}
          </button>
          {isSubmitting && <p role="status">AI is creating your quiz…</p>}
        </form>
      </main>
    );
  }

  if (result) {
    const feedback = new Map(
      result.feedback.map((item) => [item.question_id, item]),
    );
    return (
      <main className="quiz-page">
        <header className="quiz-header">
          <a href="/documents">My Materials</a>
          <div>
            <p className="eyebrow">Quiz results</p>
            <h1>{quiz.title}</h1>
          </div>
        </header>
        <section className="quiz-result-summary" aria-label="Quiz score">
          <p className="quiz-score">{result.score}%</p>
          <p>
            {result.correct_count} correct · {result.answered_count} answered ·{" "}
            {result.skipped_count} skipped
          </p>
        </section>
        <section className="quiz-review" aria-label="Question review">
          {attempt.questions.map((question) => {
            const item = feedback.get(question.id);
            if (!item) return null;
            return (
              <article className="quiz-review-card" key={question.id}>
                <h2>
                  {question.position}. {question.question}
                </h2>
                <p className={item.is_correct ? "quiz-correct" : "quiz-incorrect"}>
                  {item.is_correct ? "Correct" : item.submitted_answer == null ? "Skipped" : "Incorrect"}
                </p>
                <p>Your answer: {item.submitted_answer ?? "Not answered"}</p>
                {item.correct_answer !== undefined && (
                  <p>
                    Correct answer:{" "}
                    {Array.isArray(item.correct_answer)
                      ? item.correct_answer.join(" / ")
                      : item.correct_answer}
                  </p>
                )}
                {item.explanation && <p>{item.explanation}</p>}
                {item.citation && (
                  <div>
                    <button
                      aria-expanded={expandedCitation === question.id}
                      className="quiz-citation-button"
                      type="button"
                      onClick={() =>
                        setExpandedCitation(
                          expandedCitation === question.id ? null : question.id,
                        )
                      }
                    >
                      {citationLabel(item.citation)}
                      {item.citation.section ? ` · ${item.citation.section}` : ""}
                    </button>
                    {expandedCitation === question.id && (
                      <blockquote>{item.citation.excerpt}</blockquote>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </section>
      </main>
    );
  }

  const question = attempt.questions[questionIndex];
  return (
    <main className="quiz-page">
      <header className="quiz-header">
        <a href="/documents">My Materials</a>
        <div>
          <p className="eyebrow">Quiz player</p>
          <h1>{quiz.title}</h1>
          <p>
            Question {questionIndex + 1} / {attempt.questions.length}
          </p>
        </div>
      </header>
      {error && <p className="quiz-error" role="alert">{error}</p>}
      <section className="quiz-player-card">
        <progress
          aria-label="Quiz progress"
          max={attempt.questions.length}
          value={questionIndex + 1}
        />
        <h2>{question.question}</h2>
        {question.question_type === "fill_blank" ? (
          <label>
            Your answer
            <input
              aria-label="Your answer"
              type="text"
              value={answers[question.id] ?? ""}
              onChange={(event) =>
                setAnswers((previous) => ({
                  ...previous,
                  [question.id]: event.target.value,
                }))
              }
            />
          </label>
        ) : (
          <fieldset>
            <legend>{question.question_type === "true_false" ? "Choose true or false" : "Choose one answer"}</legend>
            {question.options.map((option) => (
              <label className="quiz-option" key={option}>
                <input
                  checked={answers[question.id] === option}
                  name={`answer-${question.id}`}
                  type="radio"
                  value={option}
                  onChange={() =>
                    setAnswers((previous) => ({
                      ...previous,
                      [question.id]: option,
                    }))
                  }
                />
                {option}
              </label>
            ))}
          </fieldset>
        )}
        <div className="quiz-player-actions">
          <button
            className="quiz-secondary-button"
            disabled={questionIndex === 0}
            type="button"
            onClick={() => setQuestionIndex((index) => Math.max(0, index - 1))}
          >
            Previous
          </button>
          <button
            className="quiz-secondary-button"
            type="button"
            onClick={() => {
              setAnswers((previous) => {
                const next = { ...previous };
                delete next[question.id];
                return next;
              });
              setQuestionIndex((index) =>
                Math.min(attempt.questions.length - 1, index + 1),
              );
            }}
          >
            Skip
          </button>
          {questionIndex < attempt.questions.length - 1 ? (
            <button
              className="quiz-primary-button"
              type="button"
              onClick={() =>
                setQuestionIndex((index) =>
                  Math.min(attempt.questions.length - 1, index + 1),
                )
              }
            >
              Next
            </button>
          ) : (
            <button
              className="quiz-primary-button"
              disabled={isSubmitting}
              type="button"
              onClick={() => setShowSubmitConfirmation(true)}
            >
              Submit quiz
            </button>
          )}
        </div>
      </section>
      {showSubmitConfirmation && (
        <div className="quiz-dialog-backdrop">
          <section
            aria-labelledby="quiz-submit-title"
            aria-modal="true"
            className="quiz-dialog"
            role="dialog"
          >
            <h2 id="quiz-submit-title">Submit quiz?</h2>
            <p>Unanswered questions will be recorded as skipped.</p>
            <div className="quiz-player-actions">
              <button
                className="quiz-secondary-button"
                type="button"
                onClick={() => setShowSubmitConfirmation(false)}
              >
                Continue quiz
              </button>
              <button
                className="quiz-primary-button"
                disabled={isSubmitting}
                type="button"
                onClick={() => void submitAnswers()}
              >
                {isSubmitting ? "Submitting…" : "Confirm submit"}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

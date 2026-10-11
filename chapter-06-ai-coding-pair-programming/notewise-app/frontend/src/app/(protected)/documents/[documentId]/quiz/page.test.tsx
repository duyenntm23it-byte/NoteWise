import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import QuizPage from "./page";

const { apiFetch, useParams } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  useParams: vi.fn(),
}));

vi.mock("../../../../../lib/api", () => ({
  apiFetch,
}));

vi.mock("next/navigation", () => ({
  useParams,
}));

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const questions = [
  {
    id: "question-1",
    position: 1,
    question: "Which answer is supported?",
    question_type: "multiple_choice",
    options: ["First", "Second"],
    citation: {
      chunk_id: "chunk-1",
      page_number: 4,
      section: "Topic",
      excerpt: "The second answer is supported by this excerpt.",
    },
  },
];

describe("QuizPage", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    useParams.mockReturnValue({ documentId: "document-1" });
    sessionStorage.clear();
  });

  it("creates a quiz, starts an attempt, submits answers and reviews the result", async () => {
    apiFetch
      .mockResolvedValueOnce(
        response({ quiz_id: "quiz-1", status: "QUEUED", job_id: "job-1" }, 202),
      )
      .mockResolvedValueOnce(
        response({
          id: "quiz-1",
          title: "Lecture review",
          status: "READY",
          questions,
        }),
      )
      .mockResolvedValueOnce(
        response(
          {
            id: "attempt-1",
            quiz_id: "quiz-1",
            status: "IN_PROGRESS",
            questions,
            result: null,
          },
          201,
        ),
      )
      .mockResolvedValueOnce(
        response({
          attempt_id: "attempt-1",
          score: 100,
          correct_count: 1,
          answered_count: 1,
          skipped_count: 0,
          submitted_at: "2026-10-11T00:00:00Z",
          feedback: [
            {
              question_id: "question-1",
              is_correct: true,
              explanation: "The source confirms the second option.",
              citation: questions[0].citation,
            },
          ],
        }),
      );
    render(<QuizPage />);

    expect(screen.getByLabelText("Number of questions")).toHaveValue("10");
    expect(screen.getByLabelText("Multiple choice")).toBeChecked();
    fireEvent.change(screen.getByLabelText("Number of questions"), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create quiz" }));

    expect(
      await screen.findByRole("heading", { name: "Which answer is supported?" }),
    ).toBeVisible();
    expect(apiFetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/documents/document-1/quizzes",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          question_count: 5,
          question_types: ["multiple_choice"],
          difficulty: "medium",
        }),
      }),
    );
    expect(apiFetch).toHaveBeenNthCalledWith(
      3,
      "/api/v1/quizzes/quiz-1/attempts",
      expect.objectContaining({ method: "POST" }),
    );

    fireEvent.click(screen.getByRole("radio", { name: "Second" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit quiz" }));
    const dialog = await screen.findByRole("dialog", { name: "Submit quiz?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirm submit" }));

    expect(await screen.findByText("100%")).toBeVisible();
    expect(screen.getByText("The source confirms the second option.")).toBeVisible();
    expect(screen.getByRole("button", { name: /Page 4/ })).toBeVisible();
    expect(apiFetch).toHaveBeenLastCalledWith(
      "/api/v1/quiz-attempts/attempt-1/submit",
      expect.objectContaining({ method: "POST" }),
    );
    await waitFor(() =>
      expect(screen.getByText("Correct")).toBeVisible(),
    );
  });

  it("requires a valid question count and retains setup when creation fails", async () => {
    render(<QuizPage />);
    fireEvent.click(screen.getByLabelText("Multiple choice"));
    fireEvent.click(screen.getByRole("button", { name: "Create quiz" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Choose at least one question type.",
    );
    expect(apiFetch).not.toHaveBeenCalled();

    fireEvent.click(screen.getByLabelText("Multiple choice"));
    const count = screen.getByLabelText("Number of questions");
    fireEvent.change(count, { target: { value: "5" } });
    apiFetch.mockResolvedValueOnce(
      response({ error: { message: "Generation unavailable." } }, 503),
    );
    fireEvent.click(screen.getByRole("button", { name: "Create quiz" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Generation unavailable.",
    );
    expect(count).toHaveValue("5");
  });

  it("restores an in-progress attempt and its selected answers after reload", async () => {
    sessionStorage.setItem(
      "notewise.quiz.document-1",
      JSON.stringify({ quizId: "quiz-1", attemptId: "attempt-1" }),
    );
    sessionStorage.setItem(
      "notewise.quiz.answers.attempt-1",
      JSON.stringify({ "question-1": "Second" }),
    );
    apiFetch
      .mockResolvedValueOnce(
        response({
          id: "quiz-1",
          title: "Lecture review",
          status: "READY",
          questions,
        }),
      )
      .mockResolvedValueOnce(
        response({
          id: "attempt-1",
          quiz_id: "quiz-1",
          status: "IN_PROGRESS",
          questions,
          result: null,
        }),
      );
    render(<QuizPage />);

    expect(
      await screen.findByRole("heading", { name: "Which answer is supported?" }),
    ).toBeVisible();
    expect(screen.getByRole("radio", { name: "Second" })).toBeChecked();
    expect(apiFetch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/quizzes/quiz-1",
    );
    expect(apiFetch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/quiz-attempts/attempt-1",
    );
  });
});

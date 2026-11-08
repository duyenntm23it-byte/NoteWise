import { expect, test } from "@playwright/test";

import {
  authMeResponse,
  mockApi,
  notFoundResponse,
  type ApiMock,
  type MockResponse,
} from "./api-mocks";

const quizId = "20000000-0000-4000-8000-000000000001";
const documentId = "30000000-0000-4000-8000-000000000001";

const questions = Array.from({ length: 5 }, (_, index) => ({
  id: `40000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
  position: index + 1,
  question_text: `Question ${index + 1}?`,
  options: [`Option ${index + 1}A`, `Option ${index + 1}B`, `Option ${index + 1}C`, `Option ${index + 1}D`],
}));

const quizDetail = {
  id: quizId,
  title: "Cell Biology Review",
  total_questions: questions.length,
  questions,
};

const quizSummaries = [
  {
    id: quizId,
    title: "Cell Biology Review",
    total_questions: 5,
    created_at: "2026-10-25T10:00:00Z",
    latest_score: 3,
  },
];

const documents = [
  {
    id: documentId,
    title: "Biology notes.pdf",
    file_type: "pdf",
    status: "ready",
    created_at: "2026-10-20T10:00:00Z",
    chunk_count: 4,
  },
];

const quizAttempt = {
  score: 1,
  total: 5,
  results: questions.map((question, index) => ({
    question_id: question.id,
    position: question.position,
    question_text: question.question_text,
    options: question.options,
    selected_index: [0, 1, null, null, null][index],
    correct_answer: 0,
    is_correct: index === 0,
    explanation: `Explanation for question ${index + 1}.`,
    source_document_title: "Biology notes.pdf",
    source_chunk_index: [0, 1, 2, null, null][index],
    source_page_number: [4, null, null, null, null][index],
  })),
};

function quizApi(submitResponse: MockResponse = { status: 200, body: quizAttempt }): ApiMock {
  return (url, method) => {
    if (url.pathname === "/api/v1/auth/me") {
      return authMeResponse();
    }
    if (url.pathname === "/api/v1/materials/" && method === "GET") {
      return { status: 200, body: documents };
    }
    if (url.pathname === "/api/v1/quizzes/" && method === "GET") {
      return { status: 200, body: quizSummaries };
    }
    if (url.pathname === `/api/v1/quizzes/${quizId}` && method === "GET") {
      return { status: 200, body: quizDetail };
    }
    if (url.pathname === `/api/v1/quizzes/${quizId}/submit` && method === "POST") {
      return submitResponse;
    }
    return notFoundResponse();
  };
}

async function openQuizPage(page: Parameters<typeof mockApi>[0], api: ApiMock): Promise<void> {
  await mockApi(page, api);
  await page.goto("/dashboard/quiz");
}

async function startQuiz(page: Parameters<typeof mockApi>[0]): Promise<void> {
  await page.getByRole("button", { name: "Start quiz" }).click();
  await expect(page.getByRole("heading", { name: "Question 1?" })).toBeVisible();
}

async function submitFromLastQuestion(page: Parameters<typeof mockApi>[0]): Promise<void> {
  await page.getByRole("button", { name: "Go to question 5" }).click();
  await page.getByRole("button", { name: "Submit quiz" }).click();
}

test("lists quizzes, navigates questions, submits and reviews the result", async ({ page }) => {
  await openQuizPage(page, quizApi());

  await expect(page.getByRole("heading", { name: "Cell Biology Review" })).toBeVisible();
  await expect(page.getByText("Latest: 3/5")).toBeVisible();
  await startQuiz(page);

  await page.getByText("Option 1A", { exact: true }).click();
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByRole("heading", { name: "Question 2?" })).toBeVisible();
  await page.getByText("Option 2B", { exact: true }).click();
  await page.getByRole("button", { name: "← Previous" }).click();
  await expect(page.getByRole("heading", { name: "Question 1?" })).toBeVisible();
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByRole("heading", { name: "Question 2?" })).toBeVisible();

  await submitFromLastQuestion(page);

  await expect(page.getByText("1 / 5", { exact: true })).toBeVisible();
  await expect(page.getByText("Question 1 · Correct")).toBeVisible();
  await expect(page.getByText("Question 2 · Review")).toBeVisible();
  await expect(page.getByText("Your answer")).toHaveCount(2);
  await expect(page.getByText("Correct answer").first()).toBeVisible();
  await expect(page.getByText("Explanation for question 1.")).toBeVisible();
  await expect(page.getByText("Source:").first()).toBeVisible();
  await expect(page.getByText("Page 4")).toBeVisible();
  await expect(page.getByText("Passage 3")).toBeVisible();
  await expect(page.getByText("Not answered").first()).toBeVisible();
});

test("shows the expired-session message when quiz submission returns 401", async ({ page }) => {
  await openQuizPage(
    page,
    quizApi({ status: 401, body: { detail: "Invalid or expired access token" } }),
  );
  await startQuiz(page);
  await submitFromLastQuestion(page);

  await expect(
    page.getByText("Your session has expired. Please log out and sign in again.", {
      exact: true,
    }),
  ).toBeVisible();
});

test("shows a friendly message when quiz submission returns 502", async ({ page }) => {
  await openQuizPage(
    page,
    quizApi({ status: 502, body: { detail: "The answer provider failed." } }),
  );
  await startQuiz(page);
  await submitFromLastQuestion(page);

  await expect(
    page.getByText("The AI could not create a valid quiz this time. Please try again.", {
      exact: true,
    }),
  ).toBeVisible();
});

test("disables quiz submission while the request is in flight", async ({ page }) => {
  let releaseSubmit!: () => void;
  const submitGate = new Promise<void>((resolve) => {
    releaseSubmit = resolve;
  });
  const delayedApi: ApiMock = async (url, method) => {
    if (url.pathname === `/api/v1/quizzes/${quizId}/submit` && method === "POST") {
      await submitGate;
      return { status: 200, body: quizAttempt };
    }
    return quizApi()(url, method);
  };

  await openQuizPage(page, delayedApi);
  await startQuiz(page);
  await page.getByRole("button", { name: "Go to question 5" }).click();
  await page.getByRole("button", { name: "Submit quiz" }).click();

  const submittingButton = page.getByRole("button", { name: "Submitting…" });
  await expect(submittingButton).toBeDisabled();
  releaseSubmit();
  await expect(page.getByText("Quiz complete")).toBeVisible();
});

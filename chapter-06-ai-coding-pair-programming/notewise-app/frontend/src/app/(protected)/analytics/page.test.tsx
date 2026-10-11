import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AnalyticsPage from "./page";

const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("../../../lib/api", () => ({ apiFetch }));

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("AnalyticsPage", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("renders overview KPI cards, weak-topic evidence and chunk-linked recommendations", async () => {
    apiFetch
      .mockResolvedValueOnce(
        response({
          average_score: 72.5,
          document_count: 4,
          completed_quiz_count: 6,
        }),
      )
      .mockResolvedValueOnce(
        response({
          accuracy: 66.67,
          correct_count: 4,
          answered_count: 6,
          skipped_count: 1,
        }),
      )
      .mockResolvedValueOnce(
        response({
          items: [
            {
              topic: "Decision Trees",
              accuracy: 33.33,
              attempts: 2,
              answered_count: 3,
              skipped_count: 1,
              sufficient_data: true,
              is_weak: true,
              reason: "Accuracy is below 60% across 2 submitted attempts.",
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        response({
          items: [
            {
              id: "recommendation-1",
              topic: "Decision Trees",
              action: "Review pruning concepts",
              reason: "Accuracy is below 60% across 2 submitted attempts.",
              document_id: "document-1",
              chunk_id: "chunk-1",
              page_start: 12,
              page_end: 12,
              created_at: "2026-10-11T00:00:00Z",
            },
          ],
        }),
      );

    render(<AnalyticsPage />);

    expect(await screen.findByText("72.5%")).toBeVisible();
    expect(screen.getByText("4")).toBeVisible();
    expect(screen.getByText("6")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Decision Trees" })).toBeVisible();
    expect(screen.getByText("33.33%")).toBeVisible();
    expect(screen.getByText("Weak topic")).toBeVisible();
    expect(screen.getByRole("link", { name: /Review pruning concepts/ })).toHaveAttribute(
      "href",
      "/documents/document-1?chunk_id=chunk-1",
    );
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(4));
  });

  it("shows a useful empty state when there is not enough topic evidence", async () => {
    apiFetch
      .mockResolvedValueOnce(
        response({ average_score: null, document_count: 0, completed_quiz_count: 0 }),
      )
      .mockResolvedValueOnce(
        response({
          accuracy: null,
          correct_count: 0,
          answered_count: 0,
          skipped_count: 0,
        }),
      )
      .mockResolvedValueOnce(response({ items: [] }))
      .mockResolvedValueOnce(response({ items: [] }));

    render(<AnalyticsPage />);

    expect(await screen.findByText("No completed quizzes yet.")).toBeVisible();
    expect(screen.getByText("No weak topics identified yet.")).toBeVisible();
    expect(screen.getByText("No study recommendations yet.")).toBeVisible();
  });
});

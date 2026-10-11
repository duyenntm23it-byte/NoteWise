import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HistoryPage from "./page";

const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("../../../lib/api", () => ({ apiFetch }));

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("HistoryPage", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("renders persisted quiz activity and pagination metadata", async () => {
    apiFetch.mockResolvedValueOnce(
      response({
        items: [
          {
            id: "history-1",
            event_type: "QUIZ_SUBMITTED",
            document_id: "document-1",
            document_title: "Decision Trees.pdf",
            occurred_at: "2026-10-11T00:00:00Z",
            details: { topic: "Decision Trees", score: 50 },
          },
        ],
        page: 1,
        page_size: 10,
        total: 12,
      }),
    );

    render(<HistoryPage />);

    expect(await screen.findByText("Decision Trees.pdf")).toBeVisible();
    expect(screen.getByText("Decision Trees")).toBeVisible();
    expect(screen.getByText("50%")).toBeVisible();
    expect(screen.getByText("Page 1 of 2")).toBeVisible();
  });

  it("shows an empty state when the student has no activity", async () => {
    apiFetch.mockResolvedValueOnce(
      response({ items: [], page: 1, page_size: 10, total: 0 }),
    );

    render(<HistoryPage />);

    expect(await screen.findByText("No learning activity yet.")).toBeVisible();
  });
});

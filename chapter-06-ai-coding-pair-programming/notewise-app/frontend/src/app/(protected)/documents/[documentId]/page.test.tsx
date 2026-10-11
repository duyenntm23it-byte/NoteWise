import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentLearningPage from "./page";

const { apiFetch, useSearchParams } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  useSearchParams: vi.fn(),
}));

vi.mock("../../../../lib/api", () => ({ apiFetch }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ documentId: "doc-1" }),
  useSearchParams,
}));

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("DocumentLearningView", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    useSearchParams.mockReturnValue({ get: () => null });
    apiFetch.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/v1/documents/doc-1") {
        return response({
          id: "doc-1",
          filename: "biology.pdf",
          media_type: "application/pdf",
          status: "READY",
          failure_code: null,
          page_count: 12,
          created_at: "2026-10-10T10:00:00Z",
          updated_at: "2026-10-10T10:00:00Z",
        });
      }
      if (path === "/api/v1/documents/doc-1/summaries") {
        return response(
          {
            summary: { id: "summary-1", status: "QUEUED", content: null },
            job_id: "job-1",
          },
          202,
        );
      }
      if (path === "/api/v1/summaries/summary-1") {
        return response({
          id: "summary-1",
          document_id: "doc-1",
          status: "READY",
          content: "# Key ideas\n\nCells carry genetic information.",
          failure_code: null,
          created_at: "2026-10-10T10:00:00Z",
        });
      }
      if (
        path === "/api/v1/documents/doc-1/questions" &&
        init?.method === "POST"
      ) {
        return response({
          status: "answered",
          answer: "Cells contain genetic information.",
          citations: [
            {
              chunk_id: "chunk-1",
              page_number: 4,
              section: "Cell structure",
              excerpt: "Cells contain genetic information.",
            },
          ],
        });
      }
      return response({ error: { message: "Unexpected request" } }, 500);
    });
  });

  it("renders the document Q&A and citation badges", async () => {
    render(<DocumentLearningPage />);

    expect(await screen.findByRole("heading", { name: "biology.pdf" })).toBeVisible();
    fireEvent.change(screen.getByLabelText("Ask about this document"), {
      target: { value: "What do cells contain?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText("Cells contain genetic information.")).toBeVisible();
    const citation = screen.getByRole("button", {
      name: "Page 4 · Cell structure",
    });
    expect(citation).toBeVisible();
    fireEvent.click(citation);
    expect(
      screen.getByRole("blockquote"),
    ).toHaveTextContent("Cells contain genetic information.");
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/v1/documents/doc-1/questions",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders a generated summary as markdown", async () => {
    render(<DocumentLearningPage />);

    fireEvent.click(await screen.findByRole("tab", { name: "Summary" }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/api/v1/documents/doc-1/summaries",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(apiFetch).toHaveBeenCalledWith("/api/v1/summaries/summary-1");
    expect(
      await screen.findByRole("heading", { name: "Key ideas" }),
    ).toBeVisible();
    expect(screen.getByText("Cells carry genetic information.")).toBeVisible();
  });

  it("clearly communicates insufficient evidence without citations", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/api/v1/documents/doc-1") {
        return response({
          id: "doc-1",
          filename: "biology.pdf",
          media_type: "application/pdf",
          status: "READY",
          failure_code: null,
          page_count: 12,
          created_at: "2026-10-10T10:00:00Z",
          updated_at: "2026-10-10T10:00:00Z",
        });
      }
      return response({
        status: "insufficient_evidence",
        answer: null,
        citations: [],
        code: "INSUFFICIENT_EVIDENCE",
      });
    });
    render(<DocumentLearningPage />);

    fireEvent.change(await screen.findByLabelText("Ask about this document"), {
      target: { value: "What is the capital of Mars?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(
      await screen.findByText(/could not find enough evidence/i),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: /Page \d+/ })).toBeNull();
  });

  it("loads and focuses the recommended source chunk from the deep link", async () => {
    useSearchParams.mockReturnValue({ get: (key: string) => key === "chunk_id" ? "chunk-1" : null });
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/api/v1/documents/doc-1") {
        return response({
          id: "doc-1",
          filename: "biology.pdf",
          media_type: "application/pdf",
          status: "READY",
          failure_code: null,
          page_count: 12,
          created_at: "2026-10-10T10:00:00Z",
          updated_at: "2026-10-10T10:00:00Z",
        });
      }
      if (path === "/api/v1/documents/doc-1/chunks/chunk-1") {
        return response({
          id: "chunk-1",
          document_id: "doc-1",
          content: "Review this passage about decision tree pruning.",
          page_number: 12,
          section: "Pruning",
        });
      }
      return response({ error: { message: "Unexpected request" } }, 500);
    });
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    render(<DocumentLearningPage />);

    expect(
      await screen.findByText("Review this passage about decision tree pruning."),
    ).toBeVisible();
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/v1/documents/doc-1/chunks/chunk-1",
    );
    expect(scrollIntoView).toHaveBeenCalled();
  });
});

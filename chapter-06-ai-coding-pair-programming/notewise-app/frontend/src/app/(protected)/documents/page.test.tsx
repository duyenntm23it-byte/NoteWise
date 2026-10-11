import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentsPage from "./page";

const { apiFetch, uploadDocument } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  uploadDocument: vi.fn(),
}));

vi.mock("../../../lib/api", () => ({
  apiFetch,
}));

vi.mock("../../../lib/documents-api", () => ({
  MAX_UPLOAD_BYTES: 25 * 1024 * 1024,
  uploadDocument,
}));

const documents = [
  {
    id: "doc-processing",
    filename: "biology.pdf",
    media_type: "application/pdf",
    status: "PROCESSING",
    failure_code: null,
    page_count: null,
    created_at: "2026-10-10T10:00:00Z",
    updated_at: "2026-10-10T10:00:00Z",
  },
  {
    id: "doc-ready",
    filename: "chemistry.docx",
    media_type:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    status: "READY",
    failure_code: null,
    page_count: 8,
    created_at: "2026-10-09T10:00:00Z",
    updated_at: "2026-10-09T10:01:00Z",
  },
  {
    id: "doc-failed",
    filename: "physics.pptx",
    media_type:
      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    status: "FAILED",
    failure_code: "DOCUMENT_UNREADABLE",
    page_count: null,
    created_at: "2026-10-08T10:00:00Z",
    updated_at: "2026-10-08T10:01:00Z",
  },
];

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("DocumentsPage", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    uploadDocument.mockReset();
    apiFetch.mockResolvedValue(
      response({ items: documents, page: 1, page_size: 20, total: 3 }),
    );
    uploadDocument.mockResolvedValue(
      response({
        document: {
          ...documents[0],
          id: "doc-new",
          filename: "new-notes.pdf",
        },
        job_id: "job-new",
      }, 202),
    );
  });

  it("renders the owned document list and lifecycle states", async () => {
    render(<DocumentsPage />);

    expect(await screen.findByText("biology.pdf")).toBeVisible();
    expect(screen.getByText("chemistry.docx")).toBeVisible();
    expect(screen.getByText("physics.pptx")).toBeVisible();
    expect(
      within(screen.getByRole("article", { name: "biology.pdf" })).getByText(
        "PROCESSING",
      ),
    ).toBeVisible();
    expect(
      within(screen.getByRole("article", { name: "chemistry.docx" })).getByText(
        "READY",
      ),
    ).toBeVisible();
    expect(
      within(screen.getByRole("article", { name: "chemistry.docx" })).getByRole(
        "link",
        { name: "Study" },
      ),
    ).toHaveAttribute("href", "/documents/doc-ready");
    expect(
      within(screen.getByRole("article", { name: "chemistry.docx" })).getByRole(
        "link",
        { name: "Take quiz" },
      ),
    ).toHaveAttribute("href", "/documents/doc-ready/quiz");
    expect(
      within(screen.getByRole("article", { name: "physics.pptx" })).getByText(
        "FAILED",
      ),
    ).toBeVisible();
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/v1/documents?page=1&page_size=20",
    );
  });

  it("uploads a selected file and reloads the document list", async () => {
    render(<DocumentsPage />);
    await screen.findByText("biology.pdf");
    const file = new File(["%PDF-1.4"], "new-notes.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(screen.getByLabelText("Choose document"), {
      target: { files: [file] },
    });

    await waitFor(() =>
      expect(uploadDocument).toHaveBeenCalledWith(file, expect.any(Function)),
    );
    expect(await screen.findByText("Upload accepted")).toBeVisible();
    expect(apiFetch).toHaveBeenLastCalledWith(
      "/api/v1/documents?page=1&page_size=20",
    );
  });

  it("offers retry only for failed documents and refreshes after retry", async () => {
    apiFetch
      .mockResolvedValueOnce(
        response({ items: documents, page: 1, page_size: 20, total: 3 }),
      )
      .mockResolvedValueOnce(response({ job_id: "retry-job", status: "QUEUED" }, 202))
      .mockResolvedValue(response({ items: documents, page: 1, page_size: 20, total: 3 }));
    render(<DocumentsPage />);

    const failedRow = await screen.findByRole("article", {
      name: "physics.pptx",
    });
    expect(within(failedRow).getByRole("button", { name: "Retry" })).toBeVisible();
    const readyRow = screen.getByRole("article", { name: "chemistry.docx" });
    expect(within(readyRow).queryByRole("button", { name: "Retry" })).toBeNull();

    fireEvent.click(within(failedRow).getByRole("button", { name: "Retry" }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/api/v1/documents/doc-failed/retry",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("requires confirmation before deleting a document", async () => {
    apiFetch
      .mockResolvedValueOnce(
        response({ items: documents, page: 1, page_size: 20, total: 3 }),
      )
      .mockResolvedValueOnce(
        response({ document_id: "doc-ready", status: "DELETING" }, 202),
      )
      .mockResolvedValue(response({ items: documents, page: 1, page_size: 20, total: 3 }));
    render(<DocumentsPage />);
    const row = await screen.findByRole("article", {
      name: "chemistry.docx",
    });

    fireEvent.click(within(row).getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Delete chemistry.docx?",
    });
    expect(apiFetch).toHaveBeenCalledTimes(1);
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(apiFetch).toHaveBeenCalledTimes(1);

    fireEvent.click(within(row).getByRole("button", { name: "Delete" }));
    fireEvent.click(
      within(
        await screen.findByRole("dialog", { name: "Delete chemistry.docx?" }),
      ).getByRole("button", { name: "Confirm delete" }),
    );

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/api/v1/documents/doc-ready",
        expect.objectContaining({ method: "DELETE" }),
      ),
    );
  });
});

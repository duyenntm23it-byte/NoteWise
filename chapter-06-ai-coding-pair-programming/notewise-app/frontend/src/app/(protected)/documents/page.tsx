"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "../../../lib/api";
import {
  type DocumentItem,
  type DocumentPage as DocumentPageResponse,
  MAX_UPLOAD_BYTES,
  uploadDocument,
} from "../../../lib/documents-api";

const PAGE_SIZE = 20;
const STATUS_FILTERS = [
  "PROCESSING",
  "READY",
  "FAILED",
  "DELETING",
  "DELETED",
] as const;

async function responseMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json();
    return payload?.error?.message ?? fallback;
  } catch {
    return fallback;
  }
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSize, setUploadSize] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentItem | null>(
    null,
  );

  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    setError("");
    const params = new URLSearchParams({
      page: "1",
      page_size: String(PAGE_SIZE),
    });
    if (statusFilter) {
      params.set("status", statusFilter);
    }
    try {
      const response = await apiFetch(`/api/v1/documents?${params.toString()}`);
      if (!response.ok) {
        throw new Error(
          await responseMessage(response, "Unable to load your documents."),
        );
      }
      const result = (await response.json()) as DocumentPageResponse;
      setDocuments(result.items);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load your documents.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!documents.some((document) => document.status === "PROCESSING")) {
      return;
    }
    const timer = window.setTimeout(() => void loadDocuments(), 2500);
    return () => window.clearTimeout(timer);
  }, [documents, loadDocuments]);

  const upload = useCallback(
    async (file: File) => {
      setError("");
      setMessage("");
      setUploadSize(file.size);
      setUploadProgress(0);
      setIsUploading(true);
      try {
        const response = await uploadDocument(file, setUploadProgress);
        if (!response.ok) {
          throw new Error(
            await responseMessage(response, "Unable to upload this document."),
          );
        }
        setMessage("Upload accepted");
        await loadDocuments();
      } catch (uploadError) {
        setError(
          uploadError instanceof Error
            ? uploadError.message
            : "Unable to upload this document.",
        );
      } finally {
        setIsUploading(false);
      }
    },
    [loadDocuments],
  );

  const runAction = useCallback(
    async (
      document: DocumentItem,
      action: "retry" | "delete",
    ) => {
      setError("");
      setMessage("");
      setPendingAction(document.id);
      try {
        const response = await apiFetch(
          action === "retry"
            ? `/api/v1/documents/${document.id}/retry`
            : `/api/v1/documents/${document.id}`,
          { method: action === "retry" ? "POST" : "DELETE" },
        );
        if (!response.ok) {
          throw new Error(
            await responseMessage(
              response,
              action === "retry"
                ? "Unable to retry document processing."
                : "Unable to delete this document.",
            ),
          );
        }
        setDocumentToDelete(null);
        await loadDocuments();
      } catch (actionError) {
        setError(
          actionError instanceof Error
            ? actionError.message
            : "Unable to update this document.",
        );
      } finally {
        setPendingAction(null);
      }
    },
    [loadDocuments],
  );

  function handleFile(file: File | undefined) {
    if (file && !isUploading) {
      void upload(file);
    }
  }

  return (
    <main className="documents-page">
      <header className="documents-header">
        <div>
          <p className="eyebrow">My learning space</p>
          <h1>My Materials</h1>
          <p className="subtle">
            Upload and manage your learning documents.
          </p>
        </div>
        <label className="documents-filter">
          <span>Filter by status</span>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All statuses</option>
            {STATUS_FILTERS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
      </header>

      <section
        className="document-dropzone"
        aria-label="Upload document"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          handleFile(event.dataTransfer.files[0]);
        }}
      >
        <p className="document-dropzone-icon" aria-hidden="true">
          ↑
        </p>
        <h2>Drop a document here</h2>
        <p>
          PDF, DOCX, or PPTX · Maximum{" "}
          {(MAX_UPLOAD_BYTES / (1024 * 1024)).toLocaleString()} MiB
        </p>
        <label className="document-upload-button">
          {isUploading ? "Uploading…" : "Upload document"}
          <input
            aria-label="Choose document"
            accept=".pdf,.docx,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation"
            disabled={isUploading}
            type="file"
            onChange={(event) => {
              handleFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
        </label>
        {isUploading && (
          <div className="upload-progress">
            <progress
              aria-label="Upload progress"
              max={100}
              value={uploadProgress}
            />
            <span>
              {uploadProgress}% · {((uploadSize ?? 0) / (1024 * 1024)).toFixed(1)}{" "}
              MiB
            </span>
          </div>
        )}
      </section>

      {message && <p role="status">{message}</p>}
      {error && <p className="document-error" role="alert">{error}</p>}

      <section className="documents-list" aria-labelledby="documents-heading">
        <div className="documents-list-heading">
          <h2 id="documents-heading">Your documents</h2>
          <button
            type="button"
            className="secondary-button"
            onClick={() => void loadDocuments()}
          >
            Refresh
          </button>
        </div>
        {isLoading ? (
          <p role="status">Loading documents…</p>
        ) : documents.length === 0 ? (
          <p className="document-empty">No documents match this filter yet.</p>
        ) : (
          <div className="document-list">
            {documents.map((document) => (
              <article
                className="document-card"
                aria-label={document.filename}
                key={document.id}
              >
                <div className="document-card-main">
                  <div className="document-file-icon" aria-hidden="true">
                    {document.filename.split(".").pop()?.toUpperCase() ?? "FILE"}
                  </div>
                  <div className="document-card-copy">
                    <h3>{document.filename}</h3>
                    <p>
                      <time dateTime={document.created_at}>
                        {new Date(document.created_at).toLocaleDateString()}
                      </time>
                      {document.page_count !== null &&
                        ` · ${document.page_count} pages`}
                    </p>
                    {document.status === "PROCESSING" && (
                      <p className="document-processing-note">
                        Processing your document…
                      </p>
                    )}
                    {document.failure_code && (
                      <p className="document-failure-note">
                        Processing failed. You can retry this document.
                      </p>
                    )}
                  </div>
                </div>
                <div className="document-card-actions">
                  <span className={`document-status status-${document.status.toLowerCase()}`}>
                    {document.status}
                  </span>
                  {document.status === "READY" && (
                    <>
                      <a className="secondary-button" href={`/documents/${document.id}`}>
                        Study
                      </a>
                      <a
                        className="secondary-button"
                        href={`/documents/${document.id}/quiz`}
                      >
                        Take quiz
                      </a>
                    </>
                  )}
                  {document.status === "FAILED" && (
                    <button
                      className="secondary-button"
                      disabled={pendingAction === document.id}
                      type="button"
                      onClick={() => void runAction(document, "retry")}
                    >
                      Retry
                    </button>
                  )}
                  {!["DELETING", "DELETED"].includes(document.status) && (
                    <button
                      className="text-button"
                      disabled={pendingAction === document.id}
                      type="button"
                      onClick={() => setDocumentToDelete(document)}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {documentToDelete && (
        <div
          className="document-dialog-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setDocumentToDelete(null);
            }
          }}
        >
          <section
            aria-labelledby="delete-dialog-title"
            aria-modal="true"
            className="document-dialog"
            role="dialog"
          >
            <h2 id="delete-dialog-title">
              Delete {documentToDelete.filename}?
            </h2>
            <p>
              The document will be removed from your materials and its stored
              content will be cleaned up.
            </p>
            <div className="document-dialog-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => setDocumentToDelete(null)}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                disabled={pendingAction === documentToDelete.id}
                type="button"
                onClick={() => void runAction(documentToDelete, "delete")}
              >
                Confirm delete
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

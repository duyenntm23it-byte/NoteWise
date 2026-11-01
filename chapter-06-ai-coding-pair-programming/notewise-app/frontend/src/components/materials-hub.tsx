"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { getStoredAccessToken, useAuth } from "@/components/auth-provider";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MAX_UPLOAD_SIZE = 20 * 1024 * 1024;

interface DocumentItem {
  id: string;
  title: string;
  file_type: "pdf" | "txt";
  status: "processing" | "ready" | "failed";
  created_at: string;
  chunk_count: number;
}

interface UploadProgress {
  fileName: string;
  percent: number;
  processing: boolean;
}

function isDocumentItem(value: unknown): value is DocumentItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "string" &&
    "title" in value &&
    typeof value.title === "string" &&
    "file_type" in value &&
    (value.file_type === "pdf" || value.file_type === "txt") &&
    "status" in value &&
    (value.status === "processing" || value.status === "ready" || value.status === "failed") &&
    "created_at" in value &&
    typeof value.created_at === "string" &&
    "chunk_count" in value &&
    typeof value.chunk_count === "number"
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

export function MaterialsHub() {
  const router = useRouter();
  const { user, isLoading, sessionError } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);

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
      setError(null);
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

  function uploadFile(file: File) {
    setError(null);
    if (!/\.(pdf|txt)$/i.test(file.name)) {
      setError("Choose a PDF or TXT file.");
      return;
    }
    if (file.size === 0) {
      setError("This file is empty. Choose a document with content.");
      return;
    }
    if (file.size > MAX_UPLOAD_SIZE) {
      setError("Files must be 20 MB or smaller.");
      return;
    }

    const token = getStoredAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    const request = new XMLHttpRequest();
    const body = new FormData();
    body.append("file", file);
    setUploadProgress({ fileName: file.name, percent: 0, processing: false });

    request.open("POST", `${API_BASE_URL}/api/v1/materials/upload`);
    request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        setUploadProgress({
          fileName: file.name,
          percent: Math.min(99, Math.round((event.loaded / event.total) * 100)),
          processing: event.loaded === event.total,
        });
      }
    };
    request.onload = () => {
      let payload: unknown;
      try {
        payload = JSON.parse(request.responseText) as unknown;
      } catch {
        setError("The server returned an unreadable response.");
        setUploadProgress(null);
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        setUploadProgress(null);
        const message = getApiError(payload);
        void loadDocuments().finally(() => setError(message));
        return;
      }
      setUploadProgress({ fileName: file.name, percent: 100, processing: false });
      void loadDocuments().finally(() => setUploadProgress(null));
    };
    request.onerror = () => {
      setError("Could not reach the server. Check your connection and try again.");
      setUploadProgress(null);
    };
    request.onabort = () => {
      setError("The upload was canceled.");
      setUploadProgress(null);
    };
    request.send(body);
  }

  function handleFileSelection(fileList: FileList | null) {
    const file = fileList?.item(0);
    if (file) {
      uploadFile(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function deleteDocument(document: DocumentItem) {
    if (!window.confirm(`Delete "${document.title}" and its processed chunks?`)) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    setDeletingDocumentId(document.id);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/materials/${document.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        let payload: unknown;
        try {
          payload = await response.json();
        } catch {
          payload = null;
        }
        throw new Error(getApiError(payload));
      }
      setDocuments((current) => current.filter((item) => item.id !== document.id));
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Could not delete the file.");
    } finally {
      setDeletingDocumentId(null);
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
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-brand">YOUR KNOWLEDGE LIBRARY</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Material Hub
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
            Upload lecture notes and PDFs. NoteWise will prepare your materials for grounded
            search and study.
          </p>
        </div>
        <span className="inline-flex w-fit rounded-full bg-white px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-slate-200">
          {documents.length} {documents.length === 1 ? "document" : "documents"}
        </span>
      </section>

      <section className="mt-8">
        <label
          htmlFor="material-upload"
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setIsDragging(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            handleFileSelection(event.dataTransfer.files);
          }}
          className={`flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-8 text-center transition sm:min-h-64 ${
            isDragging
              ? "border-brand bg-indigo-50"
              : "border-slate-300 bg-white hover:border-indigo-300 hover:bg-indigo-50/40"
          } ${uploadProgress ? "pointer-events-none opacity-70" : ""}`}
        >
          <span
            aria-hidden="true"
            className="grid h-14 w-14 place-items-center rounded-2xl bg-indigo-50 text-2xl text-brand"
          >
            ↑
          </span>
          <span className="mt-5 text-lg font-semibold text-ink">
            Drop your materials here
          </span>
          <span className="mt-2 text-sm text-slate-500">
            or <span className="font-semibold text-brand">browse files</span> from your device
          </span>
          <span className="mt-3 text-xs text-slate-400">PDF or TXT · Up to 20 MB</span>
          <input
            ref={fileInputRef}
            id="material-upload"
            type="file"
            accept=".pdf,.txt,application/pdf,text/plain"
            className="sr-only"
            disabled={Boolean(uploadProgress)}
            onChange={(event) => handleFileSelection(event.currentTarget.files)}
          />
        </label>
        {uploadProgress && (
          <div
            className="mt-4 rounded-xl border border-indigo-100 bg-white p-4"
            role="status"
            aria-live="polite"
          >
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="truncate font-medium text-ink">{uploadProgress.fileName}</span>
              <span className="shrink-0 text-slate-500">
                {uploadProgress.processing
                  ? "Processing document…"
                  : `${uploadProgress.percent}%`}
              </span>
            </div>
            <div
              className="mt-3 h-2 overflow-hidden rounded-full bg-indigo-100"
              role="progressbar"
              aria-label="Document upload and processing progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={uploadProgress.percent}
            >
              <div
                className="h-full rounded-full bg-brand transition-all duration-300"
                style={{ width: `${uploadProgress.percent}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {uploadProgress.processing
                ? "Extracting text and generating embeddings"
                : "Uploading securely"}
            </p>
          </div>
        )}
        {error && (
          <p
            role="alert"
            className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
          >
            {error}
          </p>
        )}
      </section>

      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-ink">Your materials</h2>
            <p className="mt-1 text-sm text-slate-500">
              Uploaded documents and their processing status.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadDocuments()}
            disabled={isLoadingDocuments}
            className="rounded-lg px-3 py-2 text-sm font-semibold text-brand transition hover:bg-indigo-50 disabled:opacity-50"
          >
            Refresh
          </button>
        </div>

        {isLoadingDocuments ? (
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500">
            Loading your materials…
          </div>
        ) : documents.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center">
            <p className="font-semibold text-ink">Your library is ready for its first material.</p>
            <p className="mt-2 text-sm text-slate-500">
              Upload a PDF or TXT file above to get started.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <ul className="divide-y divide-slate-100">
              {documents.map((document) => (
                <li
                  key={document.id}
                  className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"
                >
                  <div className="flex min-w-0 items-center gap-4">
                    <span
                      aria-hidden="true"
                      className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-xs font-bold uppercase text-slate-600"
                    >
                      {document.file_type}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-ink">{document.title}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {new Date(document.created_at).toLocaleDateString(undefined, {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                        {document.status === "ready" &&
                          ` · ${document.chunk_count} ${document.chunk_count === 1 ? "chunk" : "chunks"}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-4 sm:justify-end">
                    <span
                      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${
                        document.status === "ready"
                          ? "bg-emerald-50 text-emerald-700"
                          : document.status === "failed"
                            ? "bg-rose-50 text-rose-700"
                            : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      <span
                        aria-hidden="true"
                        className={`h-1.5 w-1.5 rounded-full ${
                          document.status === "ready"
                            ? "bg-emerald-500"
                            : document.status === "failed"
                              ? "bg-rose-500"
                              : "animate-pulse bg-amber-500"
                        }`}
                      />
                      {document.status === "ready"
                        ? "Ready"
                        : document.status === "failed"
                          ? "Failed"
                          : "Processing"}
                    </span>
                    <button
                      type="button"
                      onClick={() => void deleteDocument(document)}
                      disabled={deletingDocumentId === document.id}
                      aria-label={`Delete ${document.title}`}
                      className="rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-rose-50 hover:text-rose-700 focus:outline-none focus:ring-4 focus:ring-rose-100 disabled:opacity-50"
                    >
                      {deletingDocumentId === document.id ? "Deleting…" : "Delete"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </AppShell>
  );
}

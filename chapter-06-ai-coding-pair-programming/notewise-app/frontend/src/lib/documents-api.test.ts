import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ACCESS_TOKEN_KEY,
  SESSION_CHANGED_EVENT,
} from "./api";
import { uploadDocument } from "./documents-api";

class FakeXMLHttpRequest {
  upload = {
    addEventListener: vi.fn(
      (type: string, callback: (event: ProgressEvent) => void) => {
        this.uploadListeners.set(type, callback);
      },
    ),
  };
  headers = new Map<string, string>();
  listeners = new Map<string, (event: ProgressEvent) => void>();
  uploadListeners = new Map<string, (event: ProgressEvent) => void>();
  status = 202;
  statusText = "Accepted";
  responseText = '{"job_id":"job-1"}';
  sentBody: FormData | null = null;
  opened: [string, string] | null = null;

  open(method: string, url: string) {
    this.opened = [method, url];
  }

  setRequestHeader(name: string, value: string) {
    this.headers.set(name, value);
  }

  addEventListener(type: string, callback: (event: ProgressEvent) => void) {
    this.listeners.set(type, callback);
  }

  getResponseHeader() {
    return "application/json";
  }

  send(body: FormData) {
    this.sentBody = body;
  }

  emit(type: string) {
    this.listeners.get(type)?.({} as ProgressEvent);
  }
}

describe("uploadDocument", () => {
  let request: FakeXMLHttpRequest;

  beforeEach(() => {
    localStorage.clear();
    request = new FakeXMLHttpRequest();
    vi.stubGlobal("XMLHttpRequest", vi.fn(() => request));
  });

  it("sends multipart data with the Bearer token and reports transfer progress", async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, "test-access-token");
    const file = new File(["sample"], "notes.pdf", { type: "application/pdf" });
    const onProgress = vi.fn();

    const response = uploadDocument(file, onProgress);

    expect(request.opened).toEqual([
      "POST",
      "http://localhost:8000/api/v1/documents",
    ]);
    expect(request.headers.get("Authorization")).toBe("Bearer test-access-token");
    expect(request.headers.has("Content-Type")).toBe(false);
    expect(request.sentBody).toBeInstanceOf(FormData);
    expect(request.sentBody?.get("file")).toBe(file);
    request.uploadListeners.get("progress")?.({
      lengthComputable: true,
      loaded: 50,
      total: 100,
    } as ProgressEvent);
    expect(onProgress).toHaveBeenCalledWith(50);
    request.emit("load");

    const result = await response;
    expect(result.status).toBe(202);
    expect(await result.json()).toEqual({ job_id: "job-1" });
  });

  it("clears the session if the upload receives 401", async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, "expired-token");
    const sessionChanged = vi.fn();
    window.addEventListener(SESSION_CHANGED_EVENT, sessionChanged);
    request.status = 401;

    const response = uploadDocument(
      new File(["sample"], "notes.pdf", { type: "application/pdf" }),
      vi.fn(),
    );
    request.emit("load");

    expect((await response).status).toBe(401);
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    expect(sessionChanged).toHaveBeenCalledOnce();
    window.removeEventListener(SESSION_CHANGED_EVENT, sessionChanged);
  });
});

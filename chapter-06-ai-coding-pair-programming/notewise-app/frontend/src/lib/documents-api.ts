import {
  ACCESS_TOKEN_KEY,
  API_BASE_URL,
  clearAccessToken,
} from "./api";

export const MAX_UPLOAD_BYTES = Number(
  process.env.NEXT_PUBLIC_MAX_UPLOAD_BYTES ?? "26214400",
);

export interface DocumentItem {
  id: string;
  filename: string;
  media_type:
    | "application/pdf"
    | "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    | "application/vnd.openxmlformats-officedocument.presentationml.presentation";
  status: "PROCESSING" | "READY" | "FAILED" | "DELETING" | "DELETED";
  failure_code: string | null;
  page_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentPage {
  items: DocumentItem[];
  page: number;
  page_size: number;
  total: number;
}

export function uploadDocument(
  file: File,
  onProgress: (percentage: number) => void,
): Promise<Response> {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  const body = new FormData();
  body.append("file", file);

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}/api/v1/documents`);
    if (token) {
      request.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });
    request.addEventListener("load", () => {
      if (request.status === 401 && token) {
        clearAccessToken();
      }
      resolve(
        new Response(request.responseText, {
          status: request.status,
          statusText: request.statusText,
          headers: {
            "Content-Type":
              request.getResponseHeader("Content-Type") ?? "application/json",
          },
        }),
      );
    });
    request.addEventListener("error", () => {
      reject(new Error("Unable to upload the document. Check your connection."));
    });
    request.send(body);
  });
}

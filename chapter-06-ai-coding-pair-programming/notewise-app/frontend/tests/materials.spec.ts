import { expect, test } from "@playwright/test";

import {
  authMeResponse,
  mockApi,
  notFoundResponse,
  type ApiMock,
} from "./api-mocks";

const documents = [
  {
    id: "30000000-0000-4000-8000-000000000001",
    title: "Processing lecture.pdf",
    file_type: "pdf",
    status: "processing",
    created_at: "2026-10-20T10:00:00Z",
    chunk_count: 0,
  },
  {
    id: "30000000-0000-4000-8000-000000000002",
    title: "Ready lecture.pdf",
    file_type: "pdf",
    status: "ready",
    created_at: "2026-10-21T10:00:00Z",
    chunk_count: 8,
  },
  {
    id: "30000000-0000-4000-8000-000000000003",
    title: "Failed upload.txt",
    file_type: "txt",
    status: "failed",
    created_at: "2026-10-22T10:00:00Z",
    chunk_count: 0,
  },
];

function materialsApi(): ApiMock {
  return (url, method) => {
    if (url.pathname === "/api/v1/auth/me") {
      return authMeResponse();
    }
    if (url.pathname === "/api/v1/materials/" && method === "GET") {
      return { status: 200, body: documents };
    }
    if (url.pathname.endsWith(`/${documents[1].id}`) && method === "DELETE") {
      return { status: 204 };
    }
    return notFoundResponse();
  };
}

test("shows materials in processing, ready and failed states", async ({ page }) => {
  await mockApi(page, materialsApi());
  await page.goto("/dashboard/materials");

  await expect(page.getByText("Processing lecture.pdf")).toBeVisible();
  await expect(page.getByText("Ready lecture.pdf")).toBeVisible();
  await expect(page.getByText("Failed upload.txt")).toBeVisible();
  await expect(page.getByText("Processing", { exact: true })).toBeVisible();
  await expect(page.getByText("Ready", { exact: true })).toBeVisible();
  await expect(page.getByText("Failed", { exact: true })).toBeVisible();
});

test("removes a material after confirming deletion", async ({ page }) => {
  await mockApi(page, materialsApi());
  await page.goto("/dashboard/materials");
  await page.getByText("Ready lecture.pdf").waitFor();

  page.once("dialog", (dialog) => {
    void dialog.accept();
  });
  await page.getByRole("button", { name: "Delete Ready lecture.pdf" }).click();

  await expect(page.getByText("Ready lecture.pdf")).toHaveCount(0);
  await expect(page.getByText("Processing lecture.pdf")).toBeVisible();
  await expect(page.getByText("Failed upload.txt")).toBeVisible();
});

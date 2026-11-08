import { expect, test } from "@playwright/test";

test.use({ javaScriptEnabled: false });

const pages = [
  { path: "/", title: "NoteWise" },
  { path: "/login", title: "Sign in | NoteWise" },
  { path: "/dashboard", title: "Dashboard | NoteWise" },
  { path: "/dashboard/materials", title: "Material Hub | NoteWise" },
  { path: "/dashboard/chat", title: "Document Q&A | NoteWise" },
  { path: "/dashboard/quiz", title: "AI Quiz Player | NoteWise" },
  { path: "/dashboard/analytics", title: "Analytics | NoteWise" },
];

for (const pageInfo of pages) {
  test(`sets the page title for ${pageInfo.path}`, async ({ page }) => {
    await page.goto(pageInfo.path);
    await expect(page).toHaveTitle(pageInfo.title);
  });
}

for (const path of ["/login", ...pages.slice(2).map((pageInfo) => pageInfo.path)]) {
  test(`prevents indexing ${path}`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
      "content",
      "noindex, nofollow",
    );
  });
}

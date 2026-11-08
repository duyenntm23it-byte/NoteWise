import { Suspense } from "react";
import type { Metadata } from "next";

import { ChatWorkspace } from "@/components/chat-workspace";

export const metadata: Metadata = {
  title: "Document Q&A",
  description: "Ask grounded questions about your NoteWise learning materials.",
};

export default function DashboardChatPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-96 place-items-center">
          <p className="text-sm font-medium text-slate-500" role="status">
            Loading your chat…
          </p>
        </main>
      }
    >
      <ChatWorkspace />
    </Suspense>
  );
}

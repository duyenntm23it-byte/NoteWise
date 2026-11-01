import type { Metadata } from "next";

import { ChatWorkspace } from "@/components/chat-workspace";

export const metadata: Metadata = {
  title: "Document Q&A | NoteWise",
  description: "Ask grounded questions about your NoteWise learning materials.",
};

export default function DashboardChatPage() {
  return <ChatWorkspace />;
}

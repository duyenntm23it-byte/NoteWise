import type { Metadata } from "next";

import HomePage from "@/app/page";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Your personal NoteWise learning workspace and study tools.",
};

export default function DashboardPage() {
  return <HomePage />;
}

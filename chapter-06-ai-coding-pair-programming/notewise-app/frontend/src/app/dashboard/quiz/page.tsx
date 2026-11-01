import type { Metadata } from "next";

import { QuizWorkspace } from "@/components/quiz-workspace";

export const metadata: Metadata = {
  title: "AI Quiz Player | NoteWise",
  description: "Generate and play quizzes grounded in your NoteWise learning materials.",
};

export default function DashboardQuizPage() {
  return <QuizWorkspace />;
}

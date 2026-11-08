import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/components/auth-provider";
import "@/styles/globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "NoteWise",
    template: "%s | NoteWise",
  },
  description: "Organize learning materials, practice with quizzes, and track your progress.",
  openGraph: {
    siteName: "NoteWise",
    type: "website",
    locale: "en_US",
    title: "NoteWise",
    description: "Organize learning materials, practice with quizzes, and track your progress.",
  },
  twitter: {
    card: "summary_large_image",
    title: "NoteWise",
    description: "Organize learning materials, practice with quizzes, and track your progress.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

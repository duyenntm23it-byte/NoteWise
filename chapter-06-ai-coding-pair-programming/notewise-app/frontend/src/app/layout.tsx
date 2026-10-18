import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/components/auth-provider";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "NoteWise — Your learning workspace",
  description: "Organize your notes and learn with AI-powered study tools.",
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

import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "../auth/session";

import "./globals.css";

export const metadata: Metadata = {
  title: "NoteWise",
  description: "AI-powered study workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>
        <AuthProvider>
          <div className="min-h-screen bg-slate-50 text-slate-900 antialiased">
            {children}
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = {
  title: "Sign in | NoteWise",
  description: "Sign in to your NoteWise learning workspace.",
};

export default function LoginPage() {
  return <AuthForm mode="login" />;
}

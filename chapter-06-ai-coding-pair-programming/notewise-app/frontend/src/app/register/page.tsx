import type { Metadata } from "next";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = {
  title: "Create account | NoteWise",
  description: "Create an account and start learning with NoteWise.",
};

export default function RegisterPage() {
  return <AuthForm mode="register" />;
}

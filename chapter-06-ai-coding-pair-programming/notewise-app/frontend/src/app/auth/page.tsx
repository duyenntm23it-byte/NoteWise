import { Suspense } from "react";

import { AuthForm } from "./auth-form";

export default function AuthPage() {
  return (
    <Suspense fallback={<main className="auth-page">Loading…</main>}>
      <AuthForm />
    </Suspense>
  );
}

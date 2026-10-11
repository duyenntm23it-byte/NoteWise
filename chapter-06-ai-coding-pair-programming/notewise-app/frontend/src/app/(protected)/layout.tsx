"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "../../auth/session";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  const { isLoading, user, error, retryVerification, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user && !error) {
      router.replace(`/auth?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, user, error, pathname, router]);

  if (isLoading) {
    return <main role="status">Checking session…</main>;
  }
  if (error) {
    return (
      <main>
        <p role="alert">{error}</p>
        <button type="button" onClick={retryVerification}>
          Retry
        </button>
        <button type="button" onClick={logout}>
          Log out
        </button>
      </main>
    );
  }
  if (!user) {
    return <main role="status">Sign in to continue</main>;
  }
  return children;
}

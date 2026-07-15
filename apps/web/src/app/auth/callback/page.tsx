"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function Callback() {
  const params = useSearchParams();
  const router = useRouter();
  const { refresh } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setError("Missing OAuth parameters.");
      return;
    }
    api
      .githubCallback(code, state)
      .then(async () => {
        await refresh();
        router.replace("/");
      })
      .catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-md mx-auto mt-24 text-center space-y-3">
      {error ? (
        <>
          <p className="text-red-300">Sign-in failed: {error}</p>
          <a href="/login" className="btn-ghost">
            Back to sign in
          </a>
        </>
      ) : (
        <p className="text-muted">Completing sign-in…</p>
      )}
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense fallback={<p className="text-muted text-center mt-24">Loading…</p>}>
      <Callback />
    </Suspense>
  );
}

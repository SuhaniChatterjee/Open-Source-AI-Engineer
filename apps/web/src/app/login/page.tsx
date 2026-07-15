"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { GITHUB_LOGIN_URL, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AuthConfig } from "@/lib/types";

export default function LoginPage() {
  const { user, refresh } = useAuth();
  const router = useRouter();
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [devLogin, setDevLogin] = useState("suhani");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.authConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  useEffect(() => {
    if (user) router.replace("/");
  }, [user, router]);

  async function doDevLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.devLogin(devLogin.trim() || "dev");
      await refresh();
      router.replace("/");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16 space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="text-muted">
          Understand any GitHub repository in minutes.
        </p>
      </div>

      <div className="card p-6 space-y-5">
        {config?.github_enabled && (
          <a href={GITHUB_LOGIN_URL} className="btn-primary w-full justify-center">
            <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            Continue with GitHub
          </a>
        )}

        {config?.github_enabled && config?.dev_login_enabled && (
          <div className="flex items-center gap-3 text-xs text-muted">
            <div className="h-px bg-border flex-1" />
            or
            <div className="h-px bg-border flex-1" />
          </div>
        )}

        {config?.dev_login_enabled && (
          <form onSubmit={doDevLogin} className="space-y-3">
            {!config?.github_enabled && (
              <p className="text-xs text-muted">
                GitHub OAuth isn&apos;t configured, so you can use a local dev
                login to try the app. Set <code>GITHUB_CLIENT_ID</code> /{" "}
                <code>GITHUB_CLIENT_SECRET</code> to enable real sign-in.
              </p>
            )}
            <input
              className="input"
              value={devLogin}
              onChange={(e) => setDevLogin(e.target.value)}
              placeholder="dev username"
            />
            <button className="btn-ghost w-full justify-center" disabled={busy}>
              {busy ? "Signing in…" : "Continue with dev login"}
            </button>
          </form>
        )}

        {!config && <div className="text-muted text-sm">Loading…</div>}
        {error && <div className="text-red-300 text-sm">{error}</div>}
      </div>
    </div>
  );
}

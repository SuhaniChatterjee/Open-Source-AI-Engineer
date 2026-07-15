"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Repository } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";

const ACTIVE = new Set(["pending", "cloning", "parsing", "embedding", "mapping"]);

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    try {
      setRepos(await api.listRepos());
      setError(null);
    } catch (e) {
      setError((e as Error).message + " — is the API running on :8000?");
    } finally {
      setLoaded(true);
    }
  }

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  useEffect(() => {
    if (user) refresh();
  }, [user]);

  // Poll while any repo is still indexing.
  useEffect(() => {
    if (!repos.some((r) => ACTIVE.has(r.status))) return;
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, [repos]);

  async function addRepo(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.addRepo(input.trim());
      setInput("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await api.deleteRepo(id);
    refresh();
  }

  if (authLoading || !user)
    return <div className="text-muted">Loading…</div>;

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">
          Understand any repository in minutes
        </h1>
        <p className="text-muted mt-1">
          Connect a public GitHub repo. We index it, map its architecture, and
          let you ask questions with cited answers.
        </p>
      </section>

      <form onSubmit={addRepo} className="card p-4 flex gap-3">
        <input
          className="input"
          placeholder="owner/name  or  https://github.com/owner/name"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn-primary whitespace-nowrap" disabled={busy}>
          {busy ? "Indexing…" : "Index repo"}
        </button>
      </form>

      {error && (
        <div className="card p-3 border-red-500/40 text-red-300 text-sm">
          {error}
        </div>
      )}

      <section className="space-y-3">
        <h2 className="text-sm uppercase tracking-wide text-muted">
          Repositories
        </h2>
        {loaded && repos.length === 0 && (
          <div className="card p-8 text-center text-muted">
            No repositories yet. Try{" "}
            <code className="text-accent">tiangolo/fastapi</code> above.
          </div>
        )}
        <div className="grid gap-3">
          {repos.map((r) => (
            <div key={r.id} className="card p-4 flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <a
                    href={`/repos/${r.id}`}
                    className="font-medium truncate hover:text-accent"
                  >
                    {r.full_name}
                  </a>
                  <StatusBadge status={r.status} />
                </div>
                <div className="text-xs text-muted mt-1">
                  {r.status === "ready"
                    ? `${r.file_count} files · ${r.chunk_count} chunks indexed`
                    : r.error
                    ? r.error
                    : "Indexing in progress…"}
                </div>
              </div>
              <a href={`/repos/${r.id}`} className="btn-ghost">
                Open
              </a>
              <button
                onClick={() => remove(r.id)}
                className="btn-ghost text-red-300"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

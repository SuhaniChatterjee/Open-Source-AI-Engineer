"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Architecture, IndexJob, Repository } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { ArchitectureMap } from "@/components/ArchitectureMap";
import { ChatPanel } from "@/components/ChatPanel";
import { IssuesPanel } from "@/components/IssuesPanel";

const ACTIVE = new Set(["pending", "cloning", "parsing", "embedding", "mapping"]);
type Tab = "overview" | "architecture" | "issues" | "chat";

export default function RepoPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [job, setJob] = useState<IndexJob | null>(null);
  const [arch, setArch] = useState<Architecture | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const r = await api.getRepo(id);
      setRepo(r);
      try {
        setJob(await api.getStatus(id));
      } catch {
        /* no job yet */
      }
      if (r.status === "ready" && !arch) {
        setArch(await api.getArchitecture(id));
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  useEffect(() => {
    if (user) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user]);

  useEffect(() => {
    if (!repo || !ACTIVE.has(repo.status)) return;
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repo]);

  if (error)
    return (
      <div className="card p-4 text-red-300">
        {error} — <a href="/" className="underline">back</a>
      </div>
    );
  if (!repo) return <div className="text-muted">Loading…</div>;

  const indexing = ACTIVE.has(repo.status);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <a href="/" className="text-muted hover:text-gray-200">
          ←
        </a>
        <h1 className="text-xl font-semibold">{repo.full_name}</h1>
        <StatusBadge status={repo.status} />
      </div>

      {indexing && (
        <div className="card p-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-muted">
              Indexing · {job?.stage ?? repo.status}
            </span>
            <span className="text-muted">{job?.progress ?? 0}%</span>
          </div>
          <div className="h-2 bg-panel2 rounded overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent to-accent2 transition-all"
              style={{ width: `${job?.progress ?? 5}%` }}
            />
          </div>
          <p className="text-xs text-muted mt-2">
            Cloning → parsing → embedding → mapping. This runs once per repo.
          </p>
        </div>
      )}

      {repo.status === "failed" && (
        <div className="card p-4 border-red-500/40 text-red-300">
          Indexing failed: {repo.error}
        </div>
      )}

      {repo.status === "ready" && (
        <>
          <div className="flex gap-1 border-b border-border">
            {(["overview", "architecture", "issues", "chat"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm capitalize border-b-2 -mb-px ${
                  tab === t
                    ? "border-accent text-gray-100"
                    : "border-transparent text-muted hover:text-gray-300"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "overview" && (
            <div className="grid md:grid-cols-3 gap-4">
              <div className="card p-4">
                <div className="text-2xl font-semibold">{repo.file_count}</div>
                <div className="text-muted text-sm">files scanned</div>
              </div>
              <div className="card p-4">
                <div className="text-2xl font-semibold">{repo.chunk_count}</div>
                <div className="text-muted text-sm">semantic chunks</div>
              </div>
              <div className="card p-4">
                <div className="text-2xl font-semibold">
                  {repo.default_branch}
                </div>
                <div className="text-muted text-sm">default branch</div>
              </div>
              <div className="card p-4 md:col-span-3">
                <h3 className="text-sm uppercase tracking-wide text-muted mb-2">
                  README
                </h3>
                <pre className="whitespace-pre-wrap text-sm text-gray-300 font-sans max-h-72 overflow-y-auto">
                  {repo.readme_summary ?? "No README found."}
                </pre>
              </div>
            </div>
          )}

          {tab === "architecture" &&
            (arch ? (
              <ArchitectureMap arch={arch} />
            ) : (
              <div className="text-muted">Loading architecture…</div>
            ))}

          {tab === "issues" && <IssuesPanel repoId={repo.id} />}

          {tab === "chat" && <ChatPanel repoId={repo.id} />}
        </>
      )}
    </div>
  );
}

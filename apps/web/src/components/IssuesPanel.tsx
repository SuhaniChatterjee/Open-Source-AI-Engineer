"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Issue, IssueDetail } from "@/lib/types";

const LEVEL_STYLE: Record<string, string> = {
  easy: "bg-green-500/15 text-green-400",
  medium: "bg-yellow-500/15 text-yellow-400",
  hard: "bg-red-500/15 text-red-400",
};

function Suitability({ value }: { value: number | null }) {
  if (value == null) return null;
  const color =
    value >= 70 ? "text-green-400" : value >= 40 ? "text-yellow-400" : "text-red-400";
  return (
    <span className={`text-xs font-mono ${color}`} title="newcomer suitability">
      fit {value}%
    </span>
  );
}

export function IssuesPanel({ repoId }: { repoId: string }) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [detail, setDetail] = useState<IssueDetail | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [analyzing, setAnalyzing] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function load() {
    setIssues(await api.listIssues(repoId));
    setLoaded(true);
  }

  useEffect(() => {
    load().catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId]);

  async function sync() {
    setSyncing(true);
    setError(null);
    try {
      await api.syncIssues(repoId);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSyncing(false);
    }
  }

  async function analyze(number: number) {
    setAnalyzing(number);
    setError(null);
    try {
      const d = await api.analyzeIssue(repoId, number);
      setDetail(d);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAnalyzing(null);
    }
  }

  async function open(issue: Issue) {
    setError(null);
    if (issue.analysis_status === "analyzed") {
      setDetail(await api.getIssue(repoId, issue.github_number));
    } else {
      await analyze(issue.github_number);
    }
  }

  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm uppercase tracking-wide text-muted">
            Open issues {issues.length > 0 && `(${issues.length})`}
          </h3>
          <button onClick={sync} className="btn-ghost text-xs" disabled={syncing}>
            {syncing ? "Syncing…" : "Sync from GitHub"}
          </button>
        </div>

        {error && (
          <div className="card p-3 border-red-500/40 text-red-300 text-sm">{error}</div>
        )}

        {loaded && issues.length === 0 && !error && (
          <div className="card p-8 text-center text-muted text-sm">
            No issues yet. Click “Sync from GitHub” to fetch open issues.
          </div>
        )}

        <div className="space-y-2 max-h-[62vh] overflow-y-auto pr-1">
          {issues.map((issue) => (
            <button
              key={issue.id}
              onClick={() => open(issue)}
              className={`card p-3 w-full text-left hover:border-accent/50 transition-colors ${
                detail?.github_number === issue.github_number ? "border-accent" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-muted text-xs font-mono">
                  #{issue.github_number}
                </span>
                <span className="text-sm font-medium truncate flex-1">
                  {issue.title}
                </span>
                {analyzing === issue.github_number ? (
                  <span className="text-xs text-accent animate-pulse">analyzing…</span>
                ) : issue.complexity_level ? (
                  <span className={`badge ${LEVEL_STYLE[issue.complexity_level] ?? ""}`}>
                    {issue.complexity_level}
                  </span>
                ) : (
                  <span className="badge bg-panel2 text-muted">not analyzed</span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-muted">
                {issue.labels.slice(0, 3).map((l) => (
                  <span key={l} className="badge bg-panel2 text-gray-300">
                    {l}
                  </span>
                ))}
                {issue.estimated_hours && <span>~{issue.estimated_hours}</span>}
                <Suitability value={issue.suitability_score} />
                <span className="ml-auto">{issue.comments_count} comments</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div>
        {detail ? (
          <div className="card p-4 space-y-4 max-h-[68vh] overflow-y-auto">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium flex-1">
                  #{detail.github_number} {detail.title}
                </h3>
                <a
                  href={detail.html_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-accent hover:underline whitespace-nowrap"
                >
                  View on GitHub ↗
                </a>
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs">
                {detail.complexity_level && (
                  <span className={`badge ${LEVEL_STYLE[detail.complexity_level] ?? ""}`}>
                    {detail.complexity_level} · {detail.complexity_score}/10
                  </span>
                )}
                {detail.estimated_hours && (
                  <span className="text-muted">est. {detail.estimated_hours}</span>
                )}
                <Suitability value={detail.suitability_score} />
              </div>
            </div>

            {detail.required_knowledge.length > 0 && (
              <div>
                <h4 className="text-xs uppercase tracking-wide text-muted mb-1.5">
                  You should know
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {detail.required_knowledge.map((k) => (
                    <span key={k} className="badge bg-accent/10 text-accent">
                      {k}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {detail.affected_files.length > 0 && (
              <div>
                <h4 className="text-xs uppercase tracking-wide text-muted mb-1.5">
                  Likely affected files
                </h4>
                <ul className="space-y-1 text-sm font-mono">
                  {detail.affected_files.slice(0, 6).map((f, i) => (
                    <li key={i} className="text-accent truncate">
                      {f.path}:{f.start_line}-{f.end_line}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {detail.strategy && (
              <div>
                <h4 className="text-xs uppercase tracking-wide text-muted mb-1.5">
                  Implementation strategy
                </h4>
                <p className="text-sm whitespace-pre-wrap text-gray-300">
                  {detail.strategy}
                </p>
              </div>
            )}

            {detail.risks.length > 0 && (
              <div>
                <h4 className="text-xs uppercase tracking-wide text-muted mb-1.5">
                  Risks & gotchas
                </h4>
                <ul className="space-y-1 text-sm text-gray-300 list-disc list-inside">
                  {detail.risks.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-xs text-muted border-t border-border pt-2">
              Analyzed with {detail.analysis_provider ?? "—"}. Heuristic estimates —
              verify against the issue thread before starting.
            </p>
          </div>
        ) : (
          <div className="card p-8 text-center text-muted text-sm h-full flex items-center justify-center">
            Select an issue to see complexity, affected files, strategy, and risks.
          </div>
        )}
      </div>
    </div>
  );
}

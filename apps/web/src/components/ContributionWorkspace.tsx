"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Contribution, PublishPreview } from "@/lib/types";
import { DiffView } from "./DiffView";

const IN_PROGRESS = new Set(["queued", "planning", "generating"]);
const PUBLISHING = new Set(["publishing"]);

function ConfidenceBar({ score }: { score: number }) {
  const color =
    score >= 70 ? "bg-green-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-32 bg-panel2 rounded overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-mono">{score}%</span>
    </div>
  );
}

export function ContributionWorkspace({
  repoId,
  taskId,
  onBack,
}: {
  repoId: string;
  taskId: string;
  onBack: () => void;
}) {
  const [task, setTask] = useState<Contribution | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [preview, setPreview] = useState<PublishPreview | null>(null);
  const [headRepo, setHeadRepo] = useState("");
  const [publishing, setPublishing] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  async function refresh() {
    try {
      const t = await api.getContribution(repoId, taskId);
      setTask(t);
      const settled = !IN_PROGRESS.has(t.status) && !PUBLISHING.has(t.publish_status);
      if (settled && timer.current) {
        clearInterval(timer.current);
        timer.current = null;
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function loadPreview() {
    try {
      setPreview(await api.publishPreview(repoId, taskId, headRepo || undefined));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function publish() {
    setPublishing(true);
    setError(null);
    try {
      await api.publishContribution(repoId, taskId, headRepo || undefined);
      if (!timer.current) timer.current = setInterval(refresh, 1500);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPublishing(false);
    }
  }

  useEffect(() => {
    refresh();
    timer.current = setInterval(refresh, 1500);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  async function review(approve: boolean) {
    setReviewing(true);
    try {
      setTask(await api.reviewContribution(repoId, taskId, approve, note));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReviewing(false);
    }
  }

  if (error)
    return <div className="card p-4 text-red-300 text-sm">{error}</div>;
  if (!task) return <div className="text-muted">Loading…</div>;

  const working = IN_PROGRESS.has(task.status);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-muted hover:text-gray-200 text-sm">
          ← Back to issue
        </button>
        <h3 className="font-medium flex-1">
          Contribution draft · issue #{task.issue_number}
        </h3>
        {task.category && (
          <span
            className={`badge ${
              task.is_safe_category
                ? "bg-green-500/15 text-green-400"
                : "bg-yellow-500/15 text-yellow-400"
            }`}
          >
            {task.category}
            {task.is_safe_category ? " · safe" : ""}
          </span>
        )}
      </div>

      {working && (
        <div className="card p-4 text-sm text-muted animate-pulse">
          The AI engineer is {task.stage ?? task.status}… (cloning, reading files,
          drafting a change)
        </div>
      )}

      {task.status === "failed" && (
        <div className="card p-4 border-red-500/40 text-red-300 text-sm">
          Draft failed: {task.error}
        </div>
      )}

      {!working && task.confidence_score != null && (
        <div className="card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm uppercase tracking-wide text-muted">
              Confidence
            </span>
            <ConfidenceBar score={task.confidence_score} />
          </div>
          <p className="text-xs text-muted">{task.confidence_rationale}</p>
        </div>
      )}

      {/* Confidence-gated: guidance instead of a draft */}
      {task.status === "needs_guidance" && (
        <div className="card p-4 border-yellow-500/30 space-y-2">
          <h4 className="font-medium text-yellow-400">
            Not auto-drafted — guidance provided
          </h4>
          <p className="text-sm text-gray-300 whitespace-pre-wrap">
            {task.guidance}
          </p>
          <p className="text-xs text-muted border-t border-border pt-2">
            Low-confidence issues are intentionally not auto-drafted, to keep
            pull-request quality high.
          </p>
        </div>
      )}

      {/* A real draft */}
      {(task.status === "ready_for_review" ||
        task.status === "approved" ||
        task.status === "rejected") && (
        <>
          <div className="card p-4">
            <h4 className="text-sm uppercase tracking-wide text-muted mb-1">
              Summary
            </h4>
            <p className="text-sm text-gray-200">{task.summary}</p>
          </div>

          {task.plan.length > 0 && (
            <div className="card p-4">
              <h4 className="text-sm uppercase tracking-wide text-muted mb-2">
                Plan
              </h4>
              <ol className="list-decimal list-inside space-y-1 text-sm text-gray-300">
                {task.plan.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}

          <div className="space-y-3">
            <h4 className="text-sm uppercase tracking-wide text-muted">
              Proposed changes ({task.proposed_changes.length})
            </h4>
            {task.proposed_changes.map((c, i) => (
              <div key={i} className="card p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="badge bg-panel2 text-gray-300">{c.action}</span>
                  <code className="text-sm font-mono text-accent">{c.path}</code>
                </div>
                {c.note && (
                  <p className="text-xs text-yellow-400/80">{c.note}</p>
                )}
                <DiffView diff={c.diff} />
              </div>
            ))}
          </div>

          {task.risks.length > 0 && (
            <div className="card p-4">
              <h4 className="text-sm uppercase tracking-wide text-muted mb-2">
                Risks
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-300">
                {task.risks.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-3">
            <div className="card p-4">
              <h4 className="text-sm uppercase tracking-wide text-muted mb-2">
                Commit message
              </h4>
              <pre className="text-xs font-mono whitespace-pre-wrap text-gray-300">
                {task.commit_message}
              </pre>
            </div>
            <div className="card p-4">
              <h4 className="text-sm uppercase tracking-wide text-muted mb-2">
                Pull request draft
              </h4>
              <div className="text-sm font-medium mb-1">{task.pr_title}</div>
              <pre className="text-xs font-mono whitespace-pre-wrap text-gray-400 max-h-40 overflow-y-auto">
                {task.pr_body}
              </pre>
            </div>
          </div>

          {/* Human approval gate */}
          {task.status === "ready_for_review" ? (
            <div className="card p-4 space-y-3 border-accent/30">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Human review required</span>
                <span className="badge bg-panel2 text-muted">
                  nothing is pushed to GitHub
                </span>
              </div>
              <textarea
                className="input min-h-[60px]"
                placeholder="Review note (optional)…"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => review(true)}
                  className="btn-primary"
                  disabled={reviewing}
                >
                  Approve draft
                </button>
                <button
                  onClick={() => review(false)}
                  className="btn-ghost text-red-300"
                  disabled={reviewing}
                >
                  Reject
                </button>
              </div>
              <p className="text-xs text-muted">
                Approving marks this draft accepted. Opening the pull request
                requires connecting the GitHub App (a later phase) — the platform
                never pushes without explicit approval.
              </p>
            </div>
          ) : task.status === "rejected" ? (
            <div className="card p-4 border-red-500/40">
              <span className="text-red-300">
                Draft rejected
                {task.reviewer_note ? `: “${task.reviewer_note}”` : ""}
              </span>
            </div>
          ) : (
            // approved -> publish path
            <div className="card p-4 border-green-500/40 space-y-3">
              <div className="flex items-center gap-2">
                <span className="badge bg-green-500/15 text-green-400">approved</span>
                <span className="text-sm font-medium">Publish to GitHub</span>
              </div>

              {task.publish_status === "published" && task.pr_url ? (
                <div className="text-sm">
                  <span className="text-green-400">Draft PR opened:</span>{" "}
                  <a
                    href={task.pr_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent hover:underline"
                  >
                    {task.pr_url}
                  </a>
                  <div className="text-xs text-muted mt-1">
                    Branch <code>{task.branch_name}</code> on{" "}
                    <code>{task.pr_head_repo}</code>
                  </div>
                </div>
              ) : task.publish_status === "publishing" ? (
                <div className="text-sm text-muted animate-pulse">
                  Pushing branch and opening a draft PR…
                </div>
              ) : (
                <div className="space-y-3">
                  {task.publish_status === "failed" && (
                    <div className="text-sm text-red-300">
                      Publish failed: {task.publish_error}
                    </div>
                  )}
                  <input
                    className="input"
                    placeholder="your-fork-owner/repo (optional — pushes a branch there and PRs from it)"
                    value={headRepo}
                    onChange={(e) => setHeadRepo(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <button onClick={loadPreview} className="btn-ghost">
                      Preview
                    </button>
                    <button
                      onClick={publish}
                      className="btn-primary"
                      disabled={publishing}
                    >
                      {publishing ? "Publishing…" : "Open draft PR on GitHub"}
                    </button>
                  </div>

                  {preview && (
                    <div className="rounded-lg bg-bg border border-border p-3 text-xs space-y-1">
                      <div>
                        <span className="text-muted">branch:</span>{" "}
                        <code className="text-accent">{preview.branch_name}</code>
                      </div>
                      <div>
                        <span className="text-muted">into:</span>{" "}
                        <code>{preview.head_repo}</code>{" "}
                        <span className="text-muted">→ PR base</span>{" "}
                        <code>{preview.base}</code>
                      </div>
                      <div>
                        <span className="text-muted">files:</span>{" "}
                        {preview.files.join(", ")}
                      </div>
                      <div
                        className={
                          preview.token_configured
                            ? "text-green-400"
                            : "text-yellow-400"
                        }
                      >
                        {preview.token_configured
                          ? "GitHub token configured — ready to publish."
                          : "No GitHub token configured — add one in Settings to publish."}
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-muted">
                    This opens a real <strong>draft</strong> pull request under your
                    account. It requires a GitHub token (Settings) and only runs on
                    your explicit click.
                  </p>
                </div>
              )}
            </div>
          )}
        </>
      )}

      <p className="text-xs text-muted">
        Drafted with {task.provider ?? "—"}.
      </p>
    </div>
  );
}

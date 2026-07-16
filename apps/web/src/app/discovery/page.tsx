"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Insights, Opportunity, Preferences } from "@/lib/types";

const LEVELS = ["beginner", "intermediate", "advanced"];

function csv(list: string[]): string {
  return list.join(", ");
}
function parse(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function Affinities({
  title,
  items,
}: {
  title: string;
  items: { name: string; weight: number }[];
}) {
  return (
    <div>
      <div className="text-xs text-muted mb-1.5">{title}</div>
      {items.length === 0 ? (
        <span className="text-xs text-muted">—</span>
      ) : (
        <div className="space-y-1">
          {items.slice(0, 5).map((a) => (
            <div key={a.name} className="flex items-center gap-2">
              <span className="text-xs w-24 truncate">{a.name}</span>
              <div className="h-1.5 bg-panel2 rounded flex-1 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-accent to-accent2"
                  style={{ width: `${Math.max(8, a.weight * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FitBadge({ score }: { score: number }) {
  const cls =
    score >= 80
      ? "bg-green-500/15 text-green-400"
      : score >= 55
      ? "bg-yellow-500/15 text-yellow-400"
      : "bg-panel2 text-muted";
  return <span className={`badge ${cls}`}>fit {score}%</span>;
}

export default function DiscoveryPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [prefs, setPrefs] = useState<Preferences>({
    languages: [],
    topics: [],
    experience_level: "beginner",
    labels: [],
  });
  const [langs, setLangs] = useState("");
  const [topics, setTopics] = useState("");
  const [labels, setLabels] = useState("");
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!user) return;
    api.getPreferences().then((p) => {
      setPrefs(p);
      setLangs(csv(p.languages));
      setTopics(csv(p.topics));
      setLabels(csv(p.labels));
    });
    api.getInsights().then(setInsights).catch(() => {});
  }, [user]);

  function applySuggestions() {
    if (!insights) return;
    setLangs(csv([...parse(langs), ...insights.suggestions.languages]));
    setLabels(csv([...parse(labels), ...insights.suggestions.labels]));
  }

  async function search(save: boolean) {
    setLoading(true);
    setError(null);
    try {
      const next: Preferences = {
        languages: parse(langs),
        topics: parse(topics),
        labels: parse(labels),
        experience_level: prefs.experience_level,
      };
      if (save) {
        setPrefs(await api.updatePreferences(next));
      } else {
        await api.updatePreferences(next);
        setPrefs(next);
      }
      setOpps(await api.getOpportunities());
      api.getInsights().then(setInsights).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function indexRepo(fullName: string) {
    setIndexing(fullName);
    try {
      const repo = await api.addRepo(fullName);
      router.push(`/repos/${repo.id}`);
    } catch (e) {
      setError((e as Error).message);
      setIndexing(null);
    }
  }

  if (authLoading || !user) return <div className="text-muted">Loading…</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Discover contributions</h1>
        <p className="text-muted mt-1">
          Find beginner-friendly, unclaimed issues across GitHub matched to your
          interests — then index a repo to understand it in minutes.
        </p>
      </div>

      <div className="card p-4 space-y-4">
        <div className="grid md:grid-cols-3 gap-4">
          <label className="space-y-1 block">
            <span className="text-sm text-muted">Languages</span>
            <input
              className="input"
              placeholder="python, typescript"
              value={langs}
              onChange={(e) => setLangs(e.target.value)}
            />
          </label>
          <label className="space-y-1 block">
            <span className="text-sm text-muted">Interests / keywords</span>
            <input
              className="input"
              placeholder="cli, api, testing"
              value={topics}
              onChange={(e) => setTopics(e.target.value)}
            />
          </label>
          <label className="space-y-1 block">
            <span className="text-sm text-muted">Labels</span>
            <input
              className="input"
              placeholder="good first issue, help wanted"
              value={labels}
              onChange={(e) => setLabels(e.target.value)}
            />
          </label>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-muted">Experience</label>
          <select
            className="input max-w-[180px]"
            value={prefs.experience_level}
            onChange={(e) =>
              setPrefs({ ...prefs, experience_level: e.target.value })
            }
          >
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <button
            onClick={() => search(true)}
            className="btn-primary ml-auto"
            disabled={loading}
          >
            {loading ? "Searching…" : "Find opportunities"}
          </button>
        </div>
        <p className="text-xs text-muted">
          Leave labels empty to default to “good first issue” and “help wanted”.
        </p>
      </div>

      {insights?.has_history && (
        <div className="card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm uppercase tracking-wide text-muted">
              What we&apos;ve learned about you
            </h2>
            <span className="badge bg-accent/10 text-accent">personalized</span>
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-muted">
            {Object.entries(insights.stats).map(([k, v]) => (
              <span key={k}>
                <span className="text-gray-200 font-semibold">{v}</span>{" "}
                {k.replace(/_/g, " ")}
              </span>
            ))}
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            <Affinities title="Languages" items={insights.languages} />
            <Affinities title="Labels" items={insights.labels} />
            <Affinities title="Topics" items={insights.topics} />
          </div>
          {(insights.suggestions.languages.length > 0 ||
            insights.suggestions.labels.length > 0) && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted">Suggested from your history:</span>
              {[...insights.suggestions.languages, ...insights.suggestions.labels].map(
                (s) => (
                  <span key={s} className="badge bg-panel2 text-gray-300">
                    {s}
                  </span>
                )
              )}
              <button
                onClick={applySuggestions}
                className="text-accent hover:underline ml-1"
              >
                add to filters
              </button>
            </div>
          )}
          <p className="text-xs text-muted">
            Discovery uses these automatically — issues matching your track record
            are boosted, and searches fall back to what you engage with.
          </p>
        </div>
      )}

      {error && (
        <div className="card p-3 border-red-500/40 text-red-300 text-sm">{error}</div>
      )}

      <div className="space-y-3">
        {opps.map((o) => (
          <div key={`${o.repo_full_name}#${o.number}`} className="card p-4">
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <a
                    href={o.repo_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-muted hover:text-accent font-mono"
                  >
                    {o.repo_full_name}
                  </a>
                  <FitBadge score={o.fit_score} />
                </div>
                <a
                  href={o.html_url}
                  target="_blank"
                  rel="noreferrer"
                  className="block font-medium mt-1 hover:text-accent"
                >
                  #{o.number} {o.title}
                </a>
                <div className="flex flex-wrap gap-1 mt-2">
                  {o.labels.slice(0, 4).map((l) => (
                    <span key={l} className="badge bg-panel2 text-gray-300">
                      {l}
                    </span>
                  ))}
                </div>
                {o.reasons.length > 0 && (
                  <p className="text-xs text-muted mt-2">
                    Why: {o.reasons.join(" · ")} · {o.comments} comments
                  </p>
                )}
              </div>
              <button
                onClick={() => indexRepo(o.repo_full_name)}
                className="btn-ghost whitespace-nowrap"
                disabled={indexing === o.repo_full_name}
              >
                {indexing === o.repo_full_name ? "Indexing…" : "Understand repo"}
              </button>
            </div>
          </div>
        ))}
        {!loading && opps.length === 0 && (
          <div className="card p-8 text-center text-muted text-sm">
            Set your interests above and click “Find opportunities”.
          </div>
        )}
      </div>
    </div>
  );
}

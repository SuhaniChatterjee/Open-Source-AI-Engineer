"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  GitHubAppInfo,
  GitHubInstallation,
  ProviderStatus,
} from "@/lib/types";

const PROVIDERS = [
  { id: "gemini", label: "Gemini (free tier — recommended)" },
  { id: "openai", label: "OpenAI (paid)" },
  { id: "ollama", label: "Ollama (local)" },
  { id: "mock", label: "Mock (offline — lists files, no real answers)" },
];

export default function SettingsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [llm, setLlm] = useState("mock");
  const [embed, setEmbed] = useState("mock");
  const [key, setKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [ghKey, setGhKey] = useState("");
  const [ghApp, setGhApp] = useState<GitHubAppInfo | null>(null);
  const [installs, setInstalls] = useState<GitHubInstallation[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  async function load() {
    const s = await api.getProviders();
    setStatus(s);
    setLlm(s.llm_provider);
    setEmbed(s.embedding_provider);
    try {
      setGhApp(await api.githubApp());
      setInstalls(await api.githubInstallations());
    } catch {
      /* non-fatal */
    }
  }

  useEffect(() => {
    if (user) load();
  }, [user]);

  async function saveSettings() {
    setErr(null);
    setMsg(null);
    try {
      setStatus(await api.updateProviderSettings(llm, embed));
      setMsg("Provider settings saved.");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function saveKey() {
    setErr(null);
    setMsg(null);
    try {
      setStatus(await api.setProviderKey("openai", key));
      setKey("");
      setMsg("OpenAI key saved (encrypted).");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function saveGeminiKey() {
    setErr(null);
    setMsg(null);
    try {
      setStatus(await api.setProviderKey("gemini", geminiKey));
      setGeminiKey("");
      setMsg("Gemini key saved (encrypted). Re-index a repo to use it for embeddings.");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function saveGhKey() {
    setErr(null);
    setMsg(null);
    try {
      setStatus(await api.setProviderKey("github", ghKey));
      setGhKey("");
      setMsg("GitHub token saved (encrypted).");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function removeKey(provider: string) {
    setStatus(await api.deleteProviderKey(provider));
  }

  if (loading || !user) return <div className="text-muted">Loading…</div>;

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <div className="card p-5 space-y-4">
        <h2 className="font-medium">AI provider</h2>
        <p className="text-sm text-muted">
          Bring your own provider. The platform pays for no inference. Leave on{" "}
          <code>mock</code> to run fully offline.
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="space-y-1 block">
            <span className="text-sm text-muted">Chat model</span>
            <select
              className="input"
              value={llm}
              onChange={(e) => setLlm(e.target.value)}
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 block">
            <span className="text-sm text-muted">Embeddings</span>
            <select
              className="input"
              value={embed}
              onChange={(e) => setEmbed(e.target.value)}
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="text-xs text-muted">
          <strong className="text-yellow-400">Mock</strong> is an offline
          fallback: it lists matching files instead of explaining them. Pick
          Gemini or OpenAI (and save a key below) for real answers.
        </p>
        <p className="text-xs text-muted">
          Note: switching the embedding provider changes vector dimensions
          (mock 384 · gemini 768 · openai 1536) — you must{" "}
          <strong>re-index</strong> each repo after changing it.
        </p>
        <button onClick={saveSettings} className="btn-primary">
          Save providers
        </button>
      </div>

      <div className="card p-5 space-y-4">
        <h2 className="font-medium">API keys</h2>
        <div className="text-sm text-muted">
          {status &&
          Object.keys(status.configured_keys).filter((p) => p !== "github").length > 0 ? (
            <ul className="space-y-1">
              {Object.entries(status.configured_keys)
                .filter(([p]) => p !== "github")
                .map(([p, hint]) => (
                <li key={p} className="flex items-center gap-3">
                  <span className="badge bg-panel2">{p}</span>
                  <code className="font-mono">{hint}</code>
                  <button
                    onClick={() => removeKey(p)}
                    className="text-red-300 text-xs hover:underline"
                  >
                    remove
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <span>No keys configured.</span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="password"
            className="input"
            placeholder="Gemini API key (free — aistudio.google.com/apikey)"
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
          />
          <button
            onClick={saveGeminiKey}
            className="btn-ghost whitespace-nowrap"
            disabled={geminiKey.length < 8}
          >
            Save key
          </button>
        </div>
        <div className="flex gap-2">
          <input
            type="password"
            className="input"
            placeholder="OpenAI API key (sk-…)"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <button onClick={saveKey} className="btn-ghost whitespace-nowrap" disabled={key.length < 8}>
            Save key
          </button>
        </div>
        <p className="text-xs text-muted">
          Keys are encrypted at rest and never returned to the browser.
        </p>
      </div>

      <div className="card p-5 space-y-4">
        <h2 className="font-medium">GitHub publishing token</h2>
        <p className="text-sm text-muted">
          Required only to publish a pull request. Use a fine-grained token with
          Contents + Pull requests write access on your fork. Stored encrypted.
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            className="input"
            placeholder="GitHub token (github_pat_… or ghp_…)"
            value={ghKey}
            onChange={(e) => setGhKey(e.target.value)}
          />
          <button
            onClick={saveGhKey}
            className="btn-ghost whitespace-nowrap"
            disabled={ghKey.length < 8}
          >
            Save token
          </button>
        </div>
        {status?.configured_keys?.github && (
          <div className="text-sm text-muted flex items-center gap-3">
            <span className="badge bg-green-500/15 text-green-400">configured</span>
            <code className="font-mono">{status.configured_keys.github}</code>
            <button
              onClick={() => removeKey("github")}
              className="text-red-300 text-xs hover:underline"
            >
              remove
            </button>
          </div>
        )}
      </div>

      <div className="card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="font-medium">GitHub App</h2>
          {ghApp &&
            (ghApp.configured ? (
              <span className="badge bg-green-500/15 text-green-400">configured</span>
            ) : (
              <span className="badge bg-panel2 text-muted">not configured</span>
            ))}
        </div>
        <p className="text-sm text-muted">
          Installing the GitHub App lets the platform react to your repos
          (auto-reindex on push, sync issues on change) and publish pull requests
          with short-lived installation tokens instead of a personal token.
        </p>

        {ghApp?.configured && ghApp.install_url ? (
          <a href={ghApp.install_url} target="_blank" rel="noreferrer" className="btn-primary">
            Install the GitHub App
          </a>
        ) : (
          <p className="text-xs text-muted">
            Not configured on this server. Set <code>GITHUB_APP_ID</code>,{" "}
            <code>GITHUB_APP_PRIVATE_KEY</code>, <code>GITHUB_APP_SLUG</code>, and{" "}
            <code>GITHUB_WEBHOOK_SECRET</code> to enable it. A personal token
            (above) still works for publishing.
          </p>
        )}

        {installs.length > 0 && (
          <div className="space-y-1">
            <div className="text-xs uppercase tracking-wide text-muted">
              Installations
            </div>
            {installs.map((i) => (
              <div key={i.installation_id} className="flex items-center gap-3 text-sm">
                <span className="badge bg-panel2 text-gray-300">
                  {i.account_login}
                </span>
                <span className="text-muted text-xs">
                  {i.repository_selection} repos
                </span>
                {i.suspended && (
                  <span className="badge bg-red-500/15 text-red-400">suspended</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pinned so a failed save is never invisible below the fold — a silent
          error made the Save buttons look dead. */}
      {(msg || err) && (
        <div className="fixed bottom-6 right-6 z-50 max-w-md">
          <div
            className={`card p-4 shadow-xl ${
              err ? "border-red-500/50" : "border-green-500/50"
            }`}
          >
            <div className="flex items-start gap-3">
              <span className={err ? "text-red-300" : "text-green-400"}>
                {err ? "✕" : "✓"}
              </span>
              <p className={`text-sm flex-1 ${err ? "text-red-300" : "text-green-400"}`}>
                {err ?? msg}
              </p>
              <button
                onClick={() => {
                  setErr(null);
                  setMsg(null);
                }}
                className="text-muted hover:text-gray-200 text-xs"
              >
                dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

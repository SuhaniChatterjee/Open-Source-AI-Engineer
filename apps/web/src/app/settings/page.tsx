"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ProviderStatus } from "@/lib/types";

const PROVIDERS = [
  { id: "mock", label: "Mock (offline, no key)" },
  { id: "openai", label: "OpenAI (needs API key)" },
  { id: "ollama", label: "Ollama (local)" },
];

export default function SettingsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [llm, setLlm] = useState("mock");
  const [embed, setEmbed] = useState("mock");
  const [key, setKey] = useState("");
  const [ghKey, setGhKey] = useState("");
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
          Note: switching the embedding provider changes vector dimensions —
          re-index a repo after changing it.
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

      {msg && <div className="text-green-400 text-sm">{msg}</div>}
      {err && <div className="text-red-300 text-sm">{err}</div>}
    </div>
  );
}

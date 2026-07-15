"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Citation } from "@/lib/types";

interface Turn {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  provider?: string;
}

const SUGGESTIONS = [
  "What does this repository do?",
  "Explain the architecture.",
  "Which files are most important?",
  "How does authentication work?",
];

export function ChatPanel({ repoId }: { repoId: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    setTurns((t) => [...t, { role: "user", content: question }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.chat(repoId, question);
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          provider: res.provider,
        },
      ]);
    } catch (e) {
      setTurns((t) => [
        ...t,
        { role: "assistant", content: `Error: ${(e as Error).message}` },
      ]);
    } finally {
      setBusy(false);
      requestAnimationFrame(() =>
        scroller.current?.scrollTo({ top: 1e9, behavior: "smooth" })
      );
    }
  }

  return (
    <div className="card flex flex-col h-[70vh]">
      <div ref={scroller} className="flex-1 overflow-y-auto p-4 space-y-4">
        {turns.length === 0 && (
          <div className="text-center text-muted mt-10 space-y-4">
            <p>Ask anything about this repository.</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="btn-ghost text-xs"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div
            key={i}
            className={t.role === "user" ? "flex justify-end" : "flex"}
          >
            <div
              className={
                t.role === "user"
                  ? "bg-accent/15 border border-accent/30 rounded-xl px-4 py-2 max-w-[80%]"
                  : "bg-panel2 border border-border rounded-xl px-4 py-3 max-w-[85%]"
              }
            >
              <p className="whitespace-pre-wrap text-sm">{t.content}</p>
              {t.citations && t.citations.length > 0 && (
                <div className="mt-3 border-t border-border pt-2">
                  <div className="text-xs text-muted mb-1">
                    Sources ({t.provider})
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {t.citations.map((c, j) => (
                      <span
                        key={j}
                        className="badge bg-panel text-accent font-mono"
                        title={`relevance ${c.score}`}
                      >
                        {c.path}:{c.start_line}-{c.end_line}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="text-muted text-sm animate-pulse">Thinking…</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="border-t border-border p-3 flex gap-2"
      >
        <input
          className="input"
          placeholder="Ask about this repo…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn-primary" disabled={busy}>
          Send
        </button>
      </form>
    </div>
  );
}

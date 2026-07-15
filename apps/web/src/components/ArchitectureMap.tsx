import type { Architecture } from "@/lib/types";

export function ArchitectureMap({ arch }: { arch: Architecture }) {
  const maxFiles = Math.max(1, ...arch.modules.map((m) => m.file_count));
  return (
    <div className="space-y-6">
      <div className="card p-4">
        <h3 className="text-sm uppercase tracking-wide text-muted mb-2">
          Mental model
        </h3>
        <p className="text-gray-200">{arch.summary}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <h3 className="text-sm uppercase tracking-wide text-muted mb-3">
            Core modules
          </h3>
          <div className="space-y-2">
            {arch.modules.slice(0, 8).map((m) => (
              <div key={m.name}>
                <div className="flex justify-between text-sm">
                  <span className="font-mono">{m.name}</span>
                  <span className="text-muted">{m.file_count} files</span>
                </div>
                <div className="h-1.5 bg-panel2 rounded mt-1 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent to-accent2"
                    style={{ width: `${(m.file_count / maxFiles) * 100}%` }}
                  />
                </div>
                {m.roles.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {m.roles.map((role) => (
                      <span key={role} className="badge bg-panel2 text-muted">
                        {role}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="card p-4">
            <h3 className="text-sm uppercase tracking-wide text-muted mb-3">
              Detected layers
            </h3>
            <div className="flex flex-wrap gap-2">
              {arch.layers.length === 0 && (
                <span className="text-muted text-sm">
                  No conventional layers detected.
                </span>
              )}
              {arch.layers.map((l) => (
                <span key={l.role} className="badge bg-accent/10 text-accent">
                  {l.role} · {l.file_count}
                </span>
              ))}
            </div>
          </div>

          <div className="card p-4">
            <h3 className="text-sm uppercase tracking-wide text-muted mb-3">
              Start here (entry points)
            </h3>
            {arch.entry_points.length === 0 ? (
              <span className="text-muted text-sm">None detected.</span>
            ) : (
              <ul className="space-y-1 text-sm font-mono">
                {arch.entry_points.slice(0, 10).map((e) => (
                  <li key={e} className="text-accent">
                    {e}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card p-4">
            <h3 className="text-sm uppercase tracking-wide text-muted mb-3">
              Languages
            </h3>
            <div className="flex flex-wrap gap-2">
              {arch.languages.map((l) => (
                <span key={l.extension} className="badge bg-panel2 text-gray-300">
                  {l.extension || "other"} · {l.file_count}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

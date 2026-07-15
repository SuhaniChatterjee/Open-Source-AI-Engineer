const MAP: Record<string, string> = {
  ready: "bg-green-500/15 text-green-400",
  failed: "bg-red-500/15 text-red-400",
  pending: "bg-yellow-500/15 text-yellow-400",
  cloning: "bg-blue-500/15 text-blue-400",
  parsing: "bg-blue-500/15 text-blue-400",
  embedding: "bg-blue-500/15 text-blue-400",
  mapping: "bg-blue-500/15 text-blue-400",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = MAP[status] ?? "bg-panel2 text-muted";
  return <span className={`badge ${cls}`}>{status}</span>;
}

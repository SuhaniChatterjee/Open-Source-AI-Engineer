function lineClass(line: string): string {
  if (line.startsWith("+") && !line.startsWith("+++"))
    return "bg-green-500/10 text-green-300";
  if (line.startsWith("-") && !line.startsWith("---"))
    return "bg-red-500/10 text-red-300";
  if (line.startsWith("@@")) return "text-accent2";
  if (line.startsWith("+++") || line.startsWith("---")) return "text-muted";
  return "text-gray-400";
}

export function DiffView({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <pre className="text-xs font-mono overflow-x-auto rounded-lg bg-bg border border-border">
      <code className="block">
        {lines.map((line, i) => (
          <div key={i} className={`px-3 whitespace-pre ${lineClass(line)}`}>
            {line || " "}
          </div>
        ))}
      </code>
    </pre>
  );
}

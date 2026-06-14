import { Database } from "lucide-react";

type SqlAttributionProps = {
  sql: string;
};

export function SqlAttribution({ sql }: SqlAttributionProps) {
  if (!sql) return null;

  return (
    <div className="mt-3 rounded-lg border border-border bg-muted/50 p-3">
      <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Database className="size-3" aria-hidden />
        Generated SQL
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground">
        {sql}
      </pre>
    </div>
  );
}

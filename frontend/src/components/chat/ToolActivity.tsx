import { Loader2, CheckCircle2, XCircle } from "lucide-react";

import type { ToolMeta } from "@/hooks/useMessages";
import { cn } from "@/lib/utils";

type ToolActivityProps = {
  tools: ToolMeta[];
};

const statusIcon: Record<ToolMeta["status"], React.ReactNode> = {
  running: <Loader2 className="size-3 animate-spin" aria-hidden />,
  ok: <CheckCircle2 className="size-3" aria-hidden />,
  error: <XCircle className="size-3" aria-hidden />,
};

export function ToolActivity({ tools }: ToolActivityProps) {
  if (tools.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      {tools.map((tool, i) => (
        <span
          key={`${tool.name}-${i}`}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs",
            tool.status === "running" && "bg-muted text-muted-foreground",
            tool.status === "ok" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
            tool.status === "error" && "bg-destructive/10 text-destructive",
          )}
        >
          {statusIcon[tool.status]}
          {tool.name}
        </span>
      ))}
    </div>
  );
}

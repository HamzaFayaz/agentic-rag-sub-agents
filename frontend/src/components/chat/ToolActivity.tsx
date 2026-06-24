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

function formatMode(mode: string): string {
  return mode === "single_pass" ? "single pass" : "multi pass";
}

function toolLabel(tool: ToolMeta): string {
  if (tool.name !== "analyze_document") {
    return tool.name;
  }

  const file = tool.filename ?? "document";

  if (tool.status === "running") {
    if (tool.progress_pass != null && tool.progress_total != null) {
      return `analyzing ${file} (${tool.progress_pass}/${tool.progress_total})`;
    }
    return `analyzing ${file}`;
  }

  if (tool.status === "ok" && tool.mode) {
    return `analyzed ${file} (${formatMode(tool.mode)})`;
  }

  if (tool.filename) {
    return `analyzed ${file}`;
  }

  return tool.name;
}

function visibleTools(tools: ToolMeta[]): ToolMeta[] {
  let analyzeCount = 0;
  return tools.filter((tool) => {
    if (tool.name !== "analyze_document") return true;
    analyzeCount += 1;
    return analyzeCount <= 2;
  });
}

export function ToolActivity({ tools }: ToolActivityProps) {
  const chips = visibleTools(tools);
  if (chips.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      {chips.map((tool, i) => (
        <span
          key={i}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs",
            tool.status === "running" && "bg-muted text-muted-foreground",
            tool.status === "ok" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
            tool.status === "error" && "bg-destructive/10 text-destructive",
          )}
        >
          {statusIcon[tool.status]}
          {toolLabel(tool)}
        </span>
      ))}
    </div>
  );
}

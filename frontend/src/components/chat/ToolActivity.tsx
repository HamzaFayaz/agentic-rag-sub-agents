import {
  Check,
  Database,
  FileText,
  Globe,
  Loader2,
  Search,
  X,
} from "lucide-react";

import type { ToolMeta } from "@/hooks/useMessages";
import { cn } from "@/lib/utils";

type ToolActivityProps = {
  tools: ToolMeta[];
};

function shortFilename(name: string): string {
  if (name.length <= 42) return name;
  return `${name.slice(0, 20)}…${name.slice(-18)}`;
}

function toolIcon(name: string) {
  switch (name) {
    case "analyze_document":
      return FileText;
    case "search_documents":
      return Search;
    case "query_database":
      return Database;
    case "web_search":
      return Globe;
    default:
      return Search;
  }
}

function stepTitle(tool: ToolMeta): string {
  const file = tool.filename ? shortFilename(tool.filename) : null;

  if (tool.name === "analyze_document") {
    if (tool.status === "running") {
      return file ? `Reading ${file}` : "Reading document";
    }
    if (tool.status === "error") {
      return file ? `Couldn't read ${file}` : "Document read failed";
    }
    return file ? `Read ${file}` : "Document read";
  }

  if (tool.name === "search_documents") {
    if (tool.status === "running") return "Searching your documents";
    if (tool.status === "error") return "Document search failed";
    return "Searched your documents";
  }

  if (tool.name === "query_database") {
    if (tool.status === "running") return "Querying library stats";
    if (tool.status === "error") return "Library query failed";
    return "Queried library stats";
  }

  if (tool.name === "web_search") {
    if (tool.status === "running") return "Searching the web";
    if (tool.status === "error") return "Web search failed";
    return "Searched the web";
  }

  return tool.name;
}

function stepDetail(tool: ToolMeta): string | null {
  if (tool.name !== "analyze_document") return null;

  if (
    tool.status === "running" &&
    tool.progress_pass != null &&
    tool.progress_total != null &&
    tool.progress_total > 1
  ) {
    return `Section ${tool.progress_pass} of ${tool.progress_total}`;
  }

  if (tool.status === "ok" && tool.mode) {
    const mode =
      tool.mode === "single_pass" ? "Single pass" : "Multi-pass analysis";
    if (tool.passes != null && tool.passes > 1) {
      return `${mode} · ${tool.passes} steps`;
    }
    return mode;
  }

  return null;
}

function visibleTools(tools: ToolMeta[]): ToolMeta[] {
  let analyzeCount = 0;
  return tools.filter((tool) => {
    if (tool.name !== "analyze_document") return true;
    analyzeCount += 1;
    return analyzeCount <= 2;
  });
}

function StepStatus({ status }: { status: ToolMeta["status"] }) {
  if (status === "running") {
    return (
      <Loader2
        className="size-4 shrink-0 animate-spin text-muted-foreground"
        aria-hidden
      />
    );
  }
  if (status === "error") {
    return (
      <X
        className="size-4 shrink-0 text-destructive"
        aria-hidden
      />
    );
  }
  return (
    <Check
      className="size-4 shrink-0 text-muted-foreground"
      aria-hidden
    />
  );
}

function ToolStepRow({ tool }: { tool: ToolMeta }) {
  const Icon = toolIcon(tool.name);
  const detail = stepDetail(tool);
  const isRunning = tool.status === "running";

  return (
    <div className="flex gap-3 py-1.5">
      <div className="flex w-4 shrink-0 flex-col items-center pt-0.5">
        <StepStatus status={tool.status} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Icon
            className={cn(
              "size-3.5 shrink-0",
              isRunning ? "text-foreground/80" : "text-muted-foreground",
            )}
            aria-hidden
          />
          <span
            className={cn(
              "text-sm leading-snug",
              isRunning
                ? "text-foreground"
                : "text-muted-foreground",
            )}
          >
            {stepTitle(tool)}
            {isRunning && (
              <span className="inline-flex w-4">
                <span className="animate-pulse">…</span>
              </span>
            )}
          </span>
        </div>
        {detail && (
          <p className="mt-0.5 pl-5 text-xs text-muted-foreground/80">
            {detail}
          </p>
        )}
      </div>
    </div>
  );
}

export function ToolActivity({ tools }: ToolActivityProps) {
  const steps = visibleTools(tools);
  if (steps.length === 0) return null;

  const anyRunning = steps.some((t) => t.status === "running");

  return (
    <div
      className={cn(
        "mb-4 border-l-2 pl-3",
        anyRunning ? "border-foreground/25" : "border-border",
      )}
      role="status"
      aria-live="polite"
      aria-label="Assistant tool activity"
    >
      <div className="flex flex-col">
        {steps.map((tool, i) => (
          <ToolStepRow key={`${tool.name}-${tool.filename ?? ""}-${i}`} tool={tool} />
        ))}
      </div>
    </div>
  );
}

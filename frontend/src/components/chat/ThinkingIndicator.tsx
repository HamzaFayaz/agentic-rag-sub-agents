import { Loader2 } from "lucide-react";

export function ThinkingIndicator() {
  return (
    <span
      className="inline-flex items-center gap-2 text-slate-500"
      aria-label="Thinking"
    >
      <span>Thinking</span>
      <Loader2 className="size-3.5 animate-spin text-slate-400" aria-hidden />
    </span>
  );
}

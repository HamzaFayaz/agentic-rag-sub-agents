import { Loader2 } from "lucide-react";

export function ThinkingIndicator() {
  return (
    <span
      className="inline-flex items-center gap-2 text-sm text-muted-foreground"
      aria-label="Thinking"
    >
      <Loader2 className="size-3.5 animate-spin opacity-70" aria-hidden />
      <span>Thinking</span>
    </span>
  );
}

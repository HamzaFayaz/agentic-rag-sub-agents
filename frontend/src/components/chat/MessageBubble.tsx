import { cn } from "@/lib/utils";

type MessageBubbleProps = {
  role: "user" | "assistant" | "system";
  content: string;
};

export function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap",
          isUser
            ? "bg-slate-900 text-white"
            : "bg-white border border-slate-200 text-slate-900",
        )}
      >
        {content}
      </div>
    </div>
  );
}

import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator";
import {
  SourceCitations,
  type SourceCitation,
} from "@/components/chat/SourceCitations";
import { cn } from "@/lib/utils";

type MessageBubbleProps = {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceCitation[];
  isThinking?: boolean;
};

export function MessageBubble({
  role,
  content,
  sources,
  isThinking,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const showThinking = !isUser && isThinking && !content;

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-2 text-sm",
          isUser
            ? "bg-slate-900 text-white whitespace-pre-wrap"
            : "bg-white border border-slate-200 text-slate-900",
        )}
      >
        {showThinking ? (
          <ThinkingIndicator />
        ) : (
          <div className="whitespace-pre-wrap">{content}</div>
        )}
        {!isUser && sources && sources.length > 0 && (
          <SourceCitations sources={sources} />
        )}
      </div>
    </div>
  );
}

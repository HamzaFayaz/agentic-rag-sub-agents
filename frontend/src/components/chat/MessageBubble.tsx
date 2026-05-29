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

  if (isUser) {
    return (
      <div className="flex justify-end py-1">
        <div
          className={cn(
            "max-w-[85%] rounded-[1.25rem] px-4 py-2.5",
            "bg-bubble-user text-[15px] leading-relaxed text-bubble-user-fg",
            "whitespace-pre-wrap",
          )}
        >
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full py-1">
      <div className="text-[15px] leading-7 text-foreground">
        {showThinking ? (
          <ThinkingIndicator />
        ) : (
          <div className="whitespace-pre-wrap">{content}</div>
        )}
      </div>
      {!showThinking && sources && sources.length > 0 && (
        <SourceCitations sources={sources} />
      )}
    </div>
  );
}

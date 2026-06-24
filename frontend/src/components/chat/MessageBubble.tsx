import { SqlAttribution } from "@/components/chat/SqlAttribution";
import {
  SourceCitations,
  type SourceCitation,
} from "@/components/chat/SourceCitations";
import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator";
import { ToolActivity } from "@/components/chat/ToolActivity";
import { WebSourceCitations } from "@/components/chat/WebSourceCitations";
import type { ToolMeta } from "@/hooks/useMessages";
import { cn } from "@/lib/utils";

type MessageBubbleProps = {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceCitation[];
  tools?: ToolMeta[];
  isThinking?: boolean;
};

export function MessageBubble({
  role,
  content,
  sources,
  tools,
  isThinking,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const hasActiveTools = tools?.some((t) => t.status === "running") ?? false;
  const showThinking =
    !isUser && isThinking && !content && !hasActiveTools;

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

  const sqlTool = tools?.find((t) => t.sql);
  const webUrls = tools?.flatMap((t) => t.web_urls ?? []) ?? [];

  return (
    <div className="w-full py-1">
      {tools && tools.length > 0 && <ToolActivity tools={tools} />}
      <div className="text-[15px] leading-7 text-foreground">
        {showThinking ? (
          <ThinkingIndicator />
        ) : (
          <div className="whitespace-pre-wrap">{content}</div>
        )}
      </div>
      {!showThinking && sqlTool?.sql && <SqlAttribution sql={sqlTool.sql} />}
      {!showThinking && webUrls.length > 0 && (
        <WebSourceCitations urls={webUrls} />
      )}
      {!showThinking && sources && sources.length > 0 && (
        <SourceCitations sources={sources} />
      )}
    </div>
  );
}

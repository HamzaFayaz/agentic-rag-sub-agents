import type { Message } from "@/hooks/useMessages";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ScrollArea } from "@/components/ui/scroll-area";

type MessageListProps = {
  messages: Message[];
  loading?: boolean;
  streaming?: boolean;
};

export function MessageList({ messages, loading, streaming }: MessageListProps) {
  const lastMessage = messages[messages.length - 1];
  const thinkingMessageId =
    streaming &&
    lastMessage?.role === "assistant" &&
    !lastMessage.content
      ? lastMessage.id
      : null;

  return (
    <ScrollArea className="flex-1 p-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        {loading && (
          <p className="text-center text-sm text-slate-500">Loading messages…</p>
        )}
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            role={message.role}
            content={message.content}
            isThinking={message.id === thinkingMessageId}
          />
        ))}
      </div>
    </ScrollArea>
  );
}

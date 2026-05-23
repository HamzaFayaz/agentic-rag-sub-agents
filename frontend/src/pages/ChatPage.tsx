import { useEffect, useState } from "react";
import { flushSync } from "react-dom";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatLayout } from "@/components/chat/ChatLayout";
import { MessageList } from "@/components/chat/MessageList";
import { ThreadList } from "@/components/chat/ThreadList";
import { useAuth } from "@/hooks/useAuth";
import { useChatStream } from "@/hooks/useChatStream";
import { useMessages } from "@/hooks/useMessages";
import { useThreads } from "@/hooks/useThreads";

export function ChatPage() {
  const { user, session } = useAuth();
  const userId = user?.id;
  const { threads, createThread, loadThreads } = useThreads(userId);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const {
    messages,
    loading: messagesLoading,
    appendLocalMessage,
    updateLastAssistant,
    loadMessages,
  } = useMessages(activeThreadId);
  const { streaming, streamMessage, stopStreaming } = useChatStream();

  useEffect(() => {
    if (!activeThreadId && threads.length > 0) {
      setActiveThreadId(threads[0].id);
    }
  }, [threads, activeThreadId]);

  async function handleNewChat() {
    const id = await createThread();
    if (id) setActiveThreadId(id);
  }

  async function handleSend(content: string) {
    if (!activeThreadId || !session?.access_token) return;

    appendLocalMessage("user", content);
    appendLocalMessage("assistant", "");

    let assistantText = "";
    await streamMessage({
      accessToken: session.access_token,
      threadId: activeThreadId,
      content,
      onToken: (token) => {
        assistantText += token;
        flushSync(() => updateLastAssistant(assistantText));
      },
      onDone: async () => {
        await loadMessages();
        await loadThreads();
      },
      onError: (message) => {
        updateLastAssistant(`Error: ${message}`);
      },
    });
  }

  return (
    <ChatLayout
      sidebar={
        <ThreadList
          threads={threads}
          activeThreadId={activeThreadId}
          onSelect={setActiveThreadId}
          onCreate={() => void handleNewChat()}
        />
      }
    >
      {!activeThreadId ? (
        <div className="flex flex-1 items-center justify-center text-slate-500">
          Create or select a chat to begin
        </div>
      ) : (
        <>
          <MessageList
            messages={messages}
            loading={messagesLoading}
            streaming={streaming}
          />
          <ChatInput
            streaming={streaming}
            onSend={(text) => void handleSend(text)}
            onStop={stopStreaming}
          />
        </>
      )}
    </ChatLayout>
  );
}

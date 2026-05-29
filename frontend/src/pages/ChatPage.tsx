import { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { Link } from "react-router-dom";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatLayout } from "@/components/chat/ChatLayout";
import { MessageList } from "@/components/chat/MessageList";
import { ThreadList } from "@/components/chat/ThreadList";
import type { SourceCitation } from "@/components/chat/SourceCitations";
import { useAuth } from "@/hooks/useAuth";
import { useChatStream } from "@/hooks/useChatStream";
import { useDocuments } from "@/hooks/useDocuments";
import { useMessages } from "@/hooks/useMessages";
import { useThreads } from "@/hooks/useThreads";

export function ChatPage() {
  const { user, session } = useAuth();
  const userId = user?.id;
  const { threads, createThread, loadThreads } = useThreads(userId);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [queuedMessage, setQueuedMessage] = useState<string | null>(null);
  const {
    messages,
    loading: messagesLoading,
    appendLocalMessage,
    updateLastAssistant,
    loadMessages,
  } = useMessages(activeThreadId);
  const { streaming, streamMessage, stopStreaming } = useChatStream();
  const { readyCount } = useDocuments(session?.access_token);

  useEffect(() => {
    if (!activeThreadId && threads.length > 0) {
      setActiveThreadId(threads[0].id);
    }
  }, [threads, activeThreadId]);

  const sendMessage = useCallback(
    async (content: string, threadId: string) => {
      if (!session?.access_token) return;

      appendLocalMessage("user", content);
      appendLocalMessage("assistant", "");

      let assistantText = "";
      let sources: SourceCitation[] = [];
      await streamMessage({
        accessToken: session.access_token,
        threadId,
        content,
        onSources: (incoming) => {
          sources = incoming;
          flushSync(() => updateLastAssistant(assistantText, sources));
        },
        onToken: (token) => {
          assistantText += token;
          flushSync(() => updateLastAssistant(assistantText, sources));
        },
        onDone: async () => {
          await loadMessages();
          await loadThreads();
        },
        onError: (message) => {
          updateLastAssistant(`Error: ${message}`);
        },
      });
    },
    [
      session?.access_token,
      appendLocalMessage,
      updateLastAssistant,
      loadMessages,
      loadThreads,
      streamMessage,
    ],
  );

  useEffect(() => {
    if (!activeThreadId || !queuedMessage) return;
    const content = queuedMessage;
    setQueuedMessage(null);
    void sendMessage(content, activeThreadId);
  }, [activeThreadId, queuedMessage, sendMessage]);

  async function handleNewChat() {
    const id = await createThread();
    if (id) setActiveThreadId(id);
  }

  async function handleSend(content: string) {
    if (!session?.access_token) return;

    if (!activeThreadId) {
      const id = await createThread();
      if (!id) return;
      setActiveThreadId(id);
      setQueuedMessage(content);
      return;
    }

    await sendMessage(content, activeThreadId);
  }

  const isEmptyConversation =
    activeThreadId !== null &&
    !messagesLoading &&
    messages.length === 0 &&
    !streaming;

  const ragHint =
    readyCount === 0 ? (
      <div className="border-b border-border bg-warning px-4 py-2 text-center text-sm text-warning-foreground">
        Upload documents to enable RAG.{" "}
        <Link
          to="/documents"
          className="font-medium underline underline-offset-2"
        >
          Go to Documents
        </Link>
      </div>
    ) : null;

  return (
    <ChatLayout
      ragHint={ragHint}
      sidebar={
        <ThreadList
          threads={threads}
          activeThreadId={activeThreadId}
          onSelect={setActiveThreadId}
          onCreate={() => void handleNewChat()}
        />
      }
    >
      {isEmptyConversation ? (
        <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-4">
          <h1 className="mb-10 text-center text-3xl font-medium tracking-tight text-foreground">
            What can I help with?
          </h1>
          <div className="w-full max-w-3xl">
            <ChatInput
              centered
              streaming={streaming}
              onSend={(text) => void handleSend(text)}
              onStop={stopStreaming}
            />
          </div>
        </div>
      ) : activeThreadId ? (
        <div className="flex min-h-0 flex-1 flex-col">
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
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-4">
          <h1 className="mb-10 text-center text-3xl font-medium tracking-tight text-foreground">
            What can I help with?
          </h1>
          <div className="w-full max-w-3xl">
            <ChatInput
              centered
              streaming={streaming}
              onSend={(text) => void handleSend(text)}
              onStop={stopStreaming}
            />
          </div>
        </div>
      )}
    </ChatLayout>
  );
}

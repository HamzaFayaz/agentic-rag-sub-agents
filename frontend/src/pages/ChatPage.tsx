import { useEffect, useState } from "react";
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

  async function handleNewChat() {
    const id = await createThread();
    if (id) setActiveThreadId(id);
  }

  async function handleSend(content: string) {
    if (!activeThreadId || !session?.access_token) return;

    appendLocalMessage("user", content);
    appendLocalMessage("assistant", "");

    let assistantText = "";
    let sources: SourceCitation[] = [];
    await streamMessage({
      accessToken: session.access_token,
      threadId: activeThreadId,
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
  }

  const ragHint =
    readyCount === 0 ? (
      <div className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-center text-sm text-amber-900">
        Upload documents to enable RAG.{" "}
        <Link to="/documents" className="font-medium underline underline-offset-2">
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

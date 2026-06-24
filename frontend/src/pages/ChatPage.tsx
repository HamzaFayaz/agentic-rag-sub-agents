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
import type { ToolMeta } from "@/hooks/useMessages";
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
      let tools: ToolMeta[] = [];
      await streamMessage({
        accessToken: session.access_token,
        threadId,
        content,
        onSources: (incoming) => {
          sources = incoming;
          flushSync(() =>
            updateLastAssistant(assistantText, { sources, tools }),
          );
        },
        onToolStart: (payload) => {
          const started: ToolMeta = { name: payload.tool, status: "running" };
          if (payload.tool === "analyze_document") {
            const filename = payload.args.filename;
            if (typeof filename === "string") {
              started.filename = filename;
            }
          }
          tools = [...tools, started];
          flushSync(() =>
            updateLastAssistant(assistantText, { sources, tools }),
          );
        },
        onSubAgentProgress: (payload) => {
          const idx = tools.findIndex(
            (tool) =>
              tool.name === "analyze_document" &&
              tool.status === "running" &&
              (!payload.filename ||
                !tool.filename ||
                tool.filename === payload.filename),
          );
          if (idx === -1) return;

          tools = tools.map((tool, i) =>
            i === idx
              ? {
                  ...tool,
                  filename: payload.filename ?? tool.filename,
                  progress_pass: payload.pass,
                  progress_total: payload.total_passes,
                  mode: payload.mode,
                }
              : tool,
          );
          flushSync(() =>
            updateLastAssistant(assistantText, { sources, tools }),
          );
        },
        onToolEnd: (payload) => {
          const result = payload.result as
            | {
                sql?: string;
                results?: Array<{ url?: string }>;
                mode?: string;
                passes?: number;
                filename?: string;
              }
            | undefined;
          const finished: ToolMeta = {
            name: payload.tool,
            status: payload.status,
          };
          if (payload.tool === "query_database" && result?.sql) {
            finished.sql = result.sql;
          }
          if (payload.tool === "web_search" && result?.results) {
            finished.web_urls = result.results
              .map((item) => item.url)
              .filter((url): url is string => Boolean(url));
          }
          if (payload.tool === "analyze_document" && result) {
            if (result.mode) finished.mode = result.mode;
            if (result.passes != null) finished.passes = result.passes;
            if (result.filename) finished.filename = result.filename;
          }
          const endIdx = tools.findIndex(
            (tool) =>
              tool.name === payload.tool &&
              tool.status === "running" &&
              (!result?.filename || tool.filename === result.filename),
          );
          if (endIdx !== -1) {
            tools = tools.map((tool, i) =>
              i === endIdx
                ? {
                    ...finished,
                    filename: finished.filename ?? tool.filename,
                  }
                : tool,
            );
          }
          flushSync(() =>
            updateLastAssistant(assistantText, { sources, tools }),
          );
        },
        onToken: (token) => {
          assistantText += token;
          flushSync(() =>
            updateLastAssistant(assistantText, { sources, tools }),
          );
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
        <div className="flex min-h-0 flex-1 flex-col bg-background">
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

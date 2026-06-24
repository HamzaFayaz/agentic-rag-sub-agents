import { useCallback, useEffect, useState } from "react";

import type { SourceCitation } from "@/components/chat/SourceCitations";
import { supabase } from "@/lib/supabase";

export type ToolMeta = {
  name: string;
  status: "running" | "ok" | "error";
  sql?: string;
  web_urls?: string[];
  mode?: string;
  passes?: number;
  filename?: string;
  progress_pass?: number;
  progress_total?: number;
};

export type MessageMetadata = {
  sources?: SourceCitation[];
  tools?: ToolMeta[];
};

export type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  metadata?: MessageMetadata;
};

export function useMessages(threadId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const loadMessages = useCallback(async () => {
    if (!threadId) {
      setMessages([]);
      return;
    }
    setLoading(true);
    const { data, error } = await supabase
      .from("messages")
      .select("id, role, content, created_at, metadata")
      .eq("thread_id", threadId)
      .order("created_at", { ascending: true });

    setLoading(false);
    if (!error) {
      setMessages((data as Message[]) ?? []);
    }
  }, [threadId]);

  useEffect(() => {
    void loadMessages();
  }, [loadMessages]);

  const appendLocalMessage = useCallback((role: Message["role"], content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        role,
        content,
        created_at: new Date().toISOString(),
        metadata: {},
      },
    ]);
  }, []);

  const updateLastAssistant = useCallback(
    (
      content: string,
      patch?: { sources?: SourceCitation[]; tools?: ToolMeta[] },
    ) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          const merged: MessageMetadata = { ...last.metadata };
          if (patch?.sources) merged.sources = patch.sources;
          if (patch?.tools) merged.tools = patch.tools;

          next[next.length - 1] = {
            ...last,
            content,
            metadata: merged,
          };
        }
        return next;
      });
    },
    [],
  );

  return {
    messages,
    loading,
    loadMessages,
    appendLocalMessage,
    updateLastAssistant,
    setMessages,
  };
}

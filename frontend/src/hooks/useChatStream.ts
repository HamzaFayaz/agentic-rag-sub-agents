import { useCallback, useRef, useState } from "react";

import { apiBaseUrl } from "@/lib/api";
import type { SourceCitation } from "@/components/chat/SourceCitations";

export type ToolStartPayload = {
  tool: string;
  args: Record<string, unknown>;
};

export type ToolEndPayload = {
  tool: string;
  status: "ok" | "error";
  result?: unknown;
  error?: string;
};

type StreamOptions = {
  accessToken: string;
  threadId: string;
  content: string;
  onSources?: (sources: SourceCitation[]) => void;
  onToolStart?: (payload: ToolStartPayload) => void;
  onToolEnd?: (payload: ToolEndPayload) => void;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
};

function normalizeSseBuffer(raw: string): string {
  return raw.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function parseSseBlock(
  block: string,
  handlers: Pick<StreamOptions, "onSources" | "onToolStart" | "onToolEnd" | "onToken" | "onDone" | "onError">,
): void {
  const trimmed = block.trim();
  if (!trimmed || trimmed.startsWith(":")) return;

  const lines = trimmed.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^\s/, ""));
    }
  }

  if (dataLines.length === 0) return;

  const data = dataLines.join("\n");

  if (event === "sources" && handlers.onSources) {
    try {
      const sources = JSON.parse(data) as SourceCitation[];
      handlers.onSources(sources);
    } catch {
      handlers.onError(`Invalid sources data: ${data.slice(0, 80)}`);
    }
    return;
  }

  if (event === "tool_start" && handlers.onToolStart) {
    try {
      handlers.onToolStart(JSON.parse(data) as ToolStartPayload);
    } catch {
      handlers.onError(`Invalid tool_start data: ${data.slice(0, 80)}`);
    }
    return;
  }

  if (event === "tool_end" && handlers.onToolEnd) {
    try {
      handlers.onToolEnd(JSON.parse(data) as ToolEndPayload);
    } catch {
      handlers.onError(`Invalid tool_end data: ${data.slice(0, 80)}`);
    }
    return;
  }

  let payload: {
    content?: string;
    detail?: string | unknown;
    status?: string;
  };

  try {
    payload = JSON.parse(data) as typeof payload;
  } catch {
    handlers.onError(`Invalid stream data: ${data.slice(0, 80)}`);
    return;
  }

  if (event === "token" && payload.content) {
    handlers.onToken(payload.content);
  } else if (event === "error") {
    handlers.onError(
      typeof payload.detail === "string"
        ? payload.detail
        : JSON.stringify(payload.detail ?? "Stream error"),
    );
  } else if (event === "done") {
    handlers.onDone();
  }
}

function consumeSseBuffer(
  buffer: string,
  handlers: Pick<StreamOptions, "onSources" | "onToolStart" | "onToolEnd" | "onToken" | "onDone" | "onError">,
): string {
  const normalized = normalizeSseBuffer(buffer);
  const blocks = normalized.split("\n\n");
  const remainder = blocks.pop() ?? "";

  for (const block of blocks) {
    parseSseBlock(block, handlers);
  }

  return remainder;
}

export function useChatStream() {
  const [streaming, setStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const streamMessage = useCallback(async (options: StreamOptions) => {
    const {
      accessToken,
      threadId,
      content,
      onSources,
      onToolStart,
      onToolEnd,
      onToken,
      onDone,
      onError,
    } = options;

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setStreaming(true);

    let finished = false;
    const finishOnce = () => {
      if (finished) return;
      finished = true;
      onDone();
    };

    const handlers = {
      onSources,
      onToolStart,
      onToolEnd,
      onToken,
      onDone: finishOnce,
      onError: (message: string) => {
        finished = true;
        onError(message);
      },
    };

    try {
      const response = await fetch(`${apiBaseUrl()}/api/chat/stream`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ thread_id: threadId, content }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        handlers.onError(text || `Request failed (${response.status})`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        handlers.onError("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        buffer = consumeSseBuffer(buffer, handlers);
      }

      buffer += decoder.decode();
      buffer = consumeSseBuffer(buffer, handlers);
      if (buffer.trim()) {
        parseSseBlock(buffer, handlers);
      }

      finishOnce();
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        finishOnce();
        return;
      }
      handlers.onError(err instanceof Error ? err.message : "Stream failed");
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
      setStreaming(false);
    }
  }, []);

  return { streaming, streamMessage, stopStreaming };
}

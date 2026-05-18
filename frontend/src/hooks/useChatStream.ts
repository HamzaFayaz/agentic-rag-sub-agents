import { useCallback, useState } from "react";

import { apiBaseUrl } from "@/lib/api";

type StreamOptions = {
  accessToken: string;
  threadId: string;
  content: string;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
};

function parseSseChunk(
  chunk: string,
  handlers: Pick<StreamOptions, "onToken" | "onDone" | "onError">,
): void {
  const lines = chunk.split("\n");
  let event = "message";
  let data = "";

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice(5).trimStart();
    }
  }

  if (!data) return;

  const payload = JSON.parse(data) as {
    content?: string;
    detail?: string;
    status?: string;
  };

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

export function useChatStream() {
  const [streaming, setStreaming] = useState(false);

  const streamMessage = useCallback(async (options: StreamOptions) => {
    const { accessToken, threadId, content, onToken, onDone, onError } =
      options;
    setStreaming(true);

    let finished = false;
    const finishOnce = () => {
      if (finished) return;
      finished = true;
      onDone();
    };

    const handlers = {
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
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (part.trim()) parseSseChunk(part, handlers);
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) parseSseChunk(buffer, handlers);

      finishOnce();
    } catch (err) {
      handlers.onError(err instanceof Error ? err.message : "Stream failed");
    } finally {
      setStreaming(false);
    }
  }, []);

  return { streaming, streamMessage };
}

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

export function useChatStream() {
  const [streaming, setStreaming] = useState(false);

  const streamMessage = useCallback(async (options: StreamOptions) => {
    const { accessToken, threadId, content, onToken, onDone, onError } =
      options;
    setStreaming(true);

    try {
      const response = await fetch(`${apiBaseUrl()}/api/chat/stream`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ thread_id: threadId, content }),
      });

      if (!response.ok) {
        const text = await response.text();
        onError(text || `Request failed (${response.status})`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError("No response body");
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
          const lines = part.split("\n");
          let event = "message";
          let data = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              event = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              data += line.slice(5).trim();
            }
          }
          if (!data) continue;

          const payload = JSON.parse(data) as {
            content?: string;
            detail?: string;
          };

          if (event === "token" && payload.content) {
            onToken(payload.content);
          } else if (event === "error") {
            onError(payload.detail ?? "Stream error");
          } else if (event === "done") {
            onDone();
          }
        }
      }
      onDone();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Stream failed");
    } finally {
      setStreaming(false);
    }
  }, []);

  return { streaming, streamMessage };
}

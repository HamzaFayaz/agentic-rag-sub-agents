import { Square } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ChatInputProps = {
  streaming?: boolean;
  onSend: (content: string) => void;
  onStop?: () => void;
};

export function ChatInput({ streaming, onSend, onStop }: ChatInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (streaming) return;
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-slate-200 bg-white p-4"
    >
      <div className="mx-auto flex max-w-3xl gap-2">
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={streaming ? "Generating response…" : "Type a message…"}
          disabled={streaming}
        />
        {streaming ? (
          <Button
            type="button"
            className="bg-red-600 text-white hover:bg-red-700"
            onClick={() => onStop?.()}
            aria-label="Stop generating"
          >
            <Square className="size-4 fill-current" />
            Stop
          </Button>
        ) : (
          <Button type="submit" disabled={!value.trim()}>
            Send
          </Button>
        )}
      </div>
    </form>
  );
}

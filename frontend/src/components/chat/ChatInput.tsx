import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ChatInputProps = {
  disabled?: boolean;
  onSend: (content: string) => void;
};

export function ChatInput({ disabled, onSend }: ChatInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
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
          placeholder="Type a message…"
          disabled={disabled}
        />
        <Button type="submit" disabled={disabled || !value.trim()}>
          Send
        </Button>
      </div>
    </form>
  );
}

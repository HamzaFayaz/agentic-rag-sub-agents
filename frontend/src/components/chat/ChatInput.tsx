import { ArrowUp, Square } from "lucide-react";
import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ChatInputProps = {
  streaming?: boolean;
  centered?: boolean;
  onSend: (content: string) => void;
  onStop?: () => void;
};

export function ChatInput({
  streaming,
  centered = false,
  onSend,
  onStop,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    if (streaming) return;
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  const canSend = !streaming && value.trim().length > 0;

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "w-full",
        centered ? "px-0" : "bg-background px-4 pb-5 pt-2",
      )}
    >
      <div
        className={cn(
          "mx-auto flex max-w-3xl items-end gap-2 rounded-[1.75rem] border border-border/80 bg-muted/30 px-4 py-3 shadow-sm backdrop-blur-sm transition-[box-shadow,border-color] focus-within:border-border focus-within:shadow-md dark:bg-muted/20",
          centered && "shadow-md",
        )}
      >
        <textarea
          ref={textareaRef}
          rows={centered ? 2 : 1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={
            streaming ? "Generating response…" : "Ask anything…"
          }
          disabled={streaming}
          className="max-h-[200px] min-h-[24px] flex-1 resize-none bg-transparent text-[15px] leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
        />
        {streaming ? (
          <Button
            type="button"
            size="sm"
            className="h-9 shrink-0 rounded-full bg-red-600 px-3 text-white hover:bg-red-700"
            onClick={() => onStop?.()}
            aria-label="Stop generating"
          >
            <Square className="size-4 fill-current" />
          </Button>
        ) : (
          <Button
            type="submit"
            size="sm"
            disabled={!canSend}
            className="h-9 w-9 shrink-0 rounded-full p-0 disabled:opacity-40"
            aria-label="Send message"
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
      {!centered && (
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground/70">
          Enter to send · Shift+Enter for new line
        </p>
      )}
    </form>
  );
}

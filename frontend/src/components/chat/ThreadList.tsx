import { Plus } from "lucide-react";

import type { Thread } from "@/hooks/useThreads";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThreadItem } from "@/components/chat/ThreadItem";

type ThreadListProps = {
  threads: Thread[];
  activeThreadId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
};

export function ThreadList({
  threads,
  activeThreadId,
  onSelect,
  onCreate,
}: ThreadListProps) {
  return (
    <div className="flex h-full flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 p-3">
        <h2 className="text-sm font-semibold text-slate-900">Chats</h2>
        <Button variant="outline" size="sm" onClick={onCreate} aria-label="New chat">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-1">
          {threads.map((thread) => (
            <ThreadItem
              key={thread.id}
              title={thread.title}
              active={thread.id === activeThreadId}
              onClick={() => onSelect(thread.id)}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

import { type ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

type ChatLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
};

export function ChatLayout({ sidebar, children }: ChatLayoutProps) {
  const { signOut } = useAuth();

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold text-slate-900">RAG Chat</h1>
        <Button variant="outline" size="sm" onClick={() => void signOut()}>
          Log out
        </Button>
      </header>
      <div className="flex min-h-0 flex-1">
        <aside className="w-64 shrink-0">{sidebar}</aside>
        <main className="flex min-w-0 flex-1 flex-col bg-slate-50">
          {children}
        </main>
      </div>
    </div>
  );
}

import { type ReactNode } from "react";

import { AppShell } from "@/components/layout/AppShell";

type ChatLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
  ragHint?: ReactNode;
};

export function ChatLayout({ sidebar, children, ragHint }: ChatLayoutProps) {
  return (
    <AppShell title="RAG Chat" sidebar={sidebar}>
      <div className="flex min-h-0 flex-1 flex-col">
        {ragHint}
        {children}
      </div>
    </AppShell>
  );
}

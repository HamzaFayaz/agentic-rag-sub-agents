import { type ReactNode } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

type AppShellProps = {
  title: string;
  sidebar?: ReactNode;
  children: ReactNode;
};

export function AppShell({ title, sidebar, children }: AppShellProps) {
  const { signOut } = useAuth();

  return (
    <div className="flex h-screen flex-col bg-background">
      <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold text-foreground">{title}</h1>
          <AppNav />
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="outline" size="sm" onClick={() => void signOut()}>
            Log out
          </Button>
        </div>
      </header>
      {sidebar ? (
        <div className="flex min-h-0 flex-1">
          <aside className="w-64 shrink-0">{sidebar}</aside>
          <main className="flex min-w-0 flex-1 flex-col bg-background">
            {children}
          </main>
        </div>
      ) : (
        <main className="min-h-0 flex-1 overflow-auto bg-background">
          {children}
        </main>
      )}
    </div>
  );
}

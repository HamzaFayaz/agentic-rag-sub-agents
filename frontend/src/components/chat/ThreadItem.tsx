import { cn } from "@/lib/utils";

type ThreadItemProps = {
  title: string;
  active: boolean;
  onClick: () => void;
};

export function ThreadItem({ title, active, onClick }: ThreadItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full rounded-md px-3 py-2 text-left text-sm transition-colors",
        active
          ? "bg-accent text-accent-foreground"
          : "text-foreground hover:bg-muted",
      )}
    >
      <span className="line-clamp-1">{title}</span>
    </button>
  );
}

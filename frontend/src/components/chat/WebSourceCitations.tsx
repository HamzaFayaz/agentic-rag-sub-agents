import { ExternalLink } from "lucide-react";

type WebSourceCitationsProps = {
  urls: string[];
};

function displayHost(raw: string): string {
  try {
    return new URL(raw).hostname.replace(/^www\./, "");
  } catch {
    return raw;
  }
}

export function WebSourceCitations({ urls }: WebSourceCitationsProps) {
  if (urls.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {urls.map((url) => (
        <a
          key={url}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex max-w-[220px] items-center gap-1 truncate rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          title={url}
        >
          <ExternalLink className="size-3 shrink-0" aria-hidden />
          {displayHost(url)}
        </a>
      ))}
    </div>
  );
}

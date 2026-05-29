import { Badge } from "@/components/ui/badge";

export type SourceCitation = {
  document_id: string;
  filename: string;
  snippet: string;
  similarity?: number;
};

type SourceCitationsProps = {
  sources: SourceCitation[];
};

export function SourceCitations({ sources }: SourceCitationsProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">Sources:</span>
      {sources.map((source) => (
        <Badge
          key={`${source.document_id}-${source.filename}`}
          variant="outline"
          className="max-w-[200px] truncate"
          title={source.snippet}
        >
          {source.filename}
        </Badge>
      ))}
    </div>
  );
}

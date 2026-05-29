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
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {sources.map((source) => (
        <span
          key={`${source.document_id}-${source.filename}`}
          className="inline-flex max-w-[220px] truncate rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground"
          title={source.snippet}
        >
          {source.filename}
        </span>
      ))}
    </div>
  );
}

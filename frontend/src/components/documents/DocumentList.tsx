import { Loader2, Trash2 } from "lucide-react";

import { StatusBadge } from "@/components/documents/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DocumentRecord } from "@/lib/api";

type DocumentListProps = {
  documents: DocumentRecord[];
  onDelete: (id: string) => void;
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
}

export function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (documents.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-muted text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">File</th>
            <th className="px-4 py-3 font-medium">Size</th>
            <th className="px-4 py-3 font-medium">Uploaded</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium" />
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr key={doc.id} className="border-b border-border last:border-0">
              <td className="px-4 py-3 font-medium text-foreground">
                <div className="flex items-center gap-2">
                  {doc.status === "processing" && (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-600 dark:text-amber-400" />
                  )}
                  <span className="truncate">{doc.filename}</span>
                </div>
                {doc.metadata?.llm && (
                  <div className="mt-1.5 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {doc.metadata.llm.doc_type && (
                        <Badge variant="secondary" className="text-[10px]">
                          {doc.metadata.llm.doc_type}
                        </Badge>
                      )}
                      {doc.metadata.llm.topics && doc.metadata.llm.topics.length > 0 && (
                        <p
                          className="text-xs text-muted-foreground"
                          title={doc.metadata.llm.topics.join(", ")}
                        >
                          {doc.metadata.llm.topics.join(", ")}
                        </p>
                      )}
                    </div>
                    {doc.metadata.llm.summary && (
                      <p
                        className="text-xs text-muted-foreground"
                        title={doc.metadata.llm.summary}
                      >
                        {truncateText(doc.metadata.llm.summary, 120)}
                      </p>
                    )}
                  </div>
                )}
                {doc.status === "failed" && doc.error_message && (
                  <p
                    className="mt-1 truncate text-xs text-red-600 dark:text-red-400"
                    title={doc.error_message}
                  >
                    {doc.error_message}
                  </p>
                )}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {formatBytes(doc.byte_size)}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {formatDate(doc.created_at)}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={doc.status} />
              </td>
              <td className="px-4 py-3 text-right">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label={`Delete ${doc.filename}`}
                  onClick={() => {
                    if (
                      window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)
                    ) {
                      onDelete(doc.id);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

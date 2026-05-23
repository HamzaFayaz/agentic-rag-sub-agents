import { Loader2, Trash2 } from "lucide-react";

import { StatusBadge } from "@/components/documents/StatusBadge";
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

export function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (documents.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
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
            <tr key={doc.id} className="border-b border-slate-100 last:border-0">
              <td className="px-4 py-3 font-medium text-slate-900">
                <div className="flex items-center gap-2">
                  {doc.status === "processing" && (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-600" />
                  )}
                  <span className="truncate">{doc.filename}</span>
                </div>
                {doc.status === "failed" && doc.error_message && (
                  <p
                    className="mt-1 truncate text-xs text-red-600"
                    title={doc.error_message}
                  >
                    {doc.error_message}
                  </p>
                )}
              </td>
              <td className="px-4 py-3 text-slate-600">
                {formatBytes(doc.byte_size)}
              </td>
              <td className="px-4 py-3 text-slate-600">
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
                  <Trash2 className="h-4 w-4 text-slate-500" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

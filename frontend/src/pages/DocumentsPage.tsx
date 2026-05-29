import { useCallback, useRef } from "react";

import { DocumentList } from "@/components/documents/DocumentList";
import { DocumentsEmptyState } from "@/components/documents/DocumentsEmptyState";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentRealtime } from "@/hooks/useDocumentRealtime";
import { useDocuments } from "@/hooks/useDocuments";
import type { IngestAction } from "@/lib/api";

export function DocumentsPage() {
  const { user, session } = useAuth();
  const browseRef = useRef<HTMLDivElement>(null);
  const {
    documents,
    loading,
    uploading,
    error,
    upload,
    remove,
    upsertDocument,
  } = useDocuments(session?.access_token);

  const handleRealtimeUpdate = useCallback(
    (doc: Parameters<typeof upsertDocument>[0]) => {
      upsertDocument(doc);
    },
    [upsertDocument],
  );

  useDocumentRealtime({
    userId: user?.id,
    onUpdate: handleRealtimeUpdate,
  });

  return (
    <AppShell title="Documents">
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <div ref={browseRef}>
          <UploadDropzone
            uploading={uploading}
            onUpload={async (file) => {
              const doc = await upload(file);
              return doc?.ingest_action as IngestAction | undefined;
            }}
          />
        </div>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        {loading && (
          <p className="text-center text-sm text-slate-500">Loading documents…</p>
        )}

        {!loading && documents.length === 0 ? (
          <DocumentsEmptyState
            onBrowse={() =>
              browseRef.current?.querySelector<HTMLButtonElement>("button")?.click()
            }
          />
        ) : (
          <DocumentList
            documents={documents}
            onDelete={(id) => void remove(id)}
          />
        )}
      </div>
    </AppShell>
  );
}

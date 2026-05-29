import { useCallback, useEffect, useState } from "react";

import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type DocumentRecord,
} from "@/lib/api";

export function useDocuments(accessToken: string | undefined) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!accessToken) {
      setDocuments([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await listDocuments(accessToken);
      setDocuments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const upload = useCallback(
    async (file: File) => {
      if (!accessToken) return;
      setUploading(true);
      setError(null);
      try {
        const doc = await uploadDocument(accessToken, file);
        if (doc.ingest_action === "unchanged") {
          setDocuments((prev) =>
            prev.map((d) => (d.id === doc.id ? { ...d, ...doc } : d)),
          );
          return doc;
        }
        setDocuments((prev) => [doc, ...prev.filter((d) => d.id !== doc.id)]);
        await loadDocuments();
        return doc;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
        throw err;
      } finally {
        setUploading(false);
      }
    },
    [accessToken, loadDocuments],
  );

  const remove = useCallback(
    async (documentId: string) => {
      if (!accessToken) return;
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      try {
        await deleteDocument(accessToken, documentId);
      } catch (err) {
        await loadDocuments();
        setError(err instanceof Error ? err.message : "Delete failed");
        throw err;
      }
    },
    [accessToken, loadDocuments],
  );

  const upsertDocument = useCallback((doc: DocumentRecord) => {
    setDocuments((prev) => {
      const index = prev.findIndex((d) => d.id === doc.id);
      if (index === -1) return [doc, ...prev];
      const next = [...prev];
      next[index] = { ...next[index], ...doc };
      return next;
    });
  }, []);

  const readyCount = documents.filter((d) => d.status === "ready").length;

  return {
    documents,
    loading,
    uploading,
    error,
    readyCount,
    loadDocuments,
    upload,
    remove,
    upsertDocument,
  };
}

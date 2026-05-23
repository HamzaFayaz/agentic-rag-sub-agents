import { useEffect } from "react";

import type { DocumentRecord } from "@/lib/api";
import { supabase } from "@/lib/supabase";

type UseDocumentRealtimeOptions = {
  userId: string | undefined;
  onUpdate: (doc: DocumentRecord) => void;
};

export function useDocumentRealtime({
  userId,
  onUpdate,
}: UseDocumentRealtimeOptions) {
  useEffect(() => {
    if (!userId) return;

    const channel = supabase
      .channel(`documents:${userId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "documents",
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          const row = payload.new as Record<string, unknown> | null;
          if (!row || typeof row.id !== "string") return;

          onUpdate({
            id: row.id,
            filename: String(row.filename ?? ""),
            status: row.status as DocumentRecord["status"],
            byte_size: Number(row.byte_size ?? 0),
            error_message:
              row.error_message != null ? String(row.error_message) : null,
            created_at: String(row.created_at ?? new Date().toISOString()),
          });
        },
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [userId, onUpdate]);
}

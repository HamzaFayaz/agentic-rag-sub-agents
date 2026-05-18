import { useCallback, useEffect, useState } from "react";

import { supabase } from "@/lib/supabase";

export type Thread = {
  id: string;
  title: string;
  updated_at: string;
};

export function useThreads(userId: string | undefined) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadThreads = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    const { data, error: fetchError } = await supabase
      .from("threads")
      .select("id, title, updated_at")
      .order("updated_at", { ascending: false });

    setLoading(false);
    if (fetchError) {
      setError(fetchError.message);
      return;
    }
    setThreads(data ?? []);
  }, [userId]);

  useEffect(() => {
    void loadThreads();
  }, [loadThreads]);

  const createThread = useCallback(async () => {
    if (!userId) return null;
    const { data, error: insertError } = await supabase
      .from("threads")
      .insert({ user_id: userId, title: "New chat" })
      .select("id, title, updated_at")
      .single();

    if (insertError) {
      setError(insertError.message);
      return null;
    }
    setThreads((prev) => [data, ...prev]);
    return data.id as string;
  }, [userId]);

  return { threads, loading, error, loadThreads, createThread };
}

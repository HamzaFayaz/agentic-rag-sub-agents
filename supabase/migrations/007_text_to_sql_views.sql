-- Module 7 (Track A-T1): read-only views for text-to-sql
-- Layer 1 safety: views exclude content and embedding columns entirely.
-- All views use SECURITY INVOKER so RLS filters by the calling user's JWT.

-- v_user_document_stats: document-level stats with chunk count
create or replace view public.v_user_document_stats
with (security_invoker = true)
as
  select
    d.id,
    d.filename,
    d.status,
    d.mime_type,
    d.byte_size,
    d.created_at,
    d.metadata,
    coalesce(c.chunk_count, 0) as chunk_count
  from public.documents d
  left join (
    select document_id, count(*)::int as chunk_count
    from public.document_chunks
    group by document_id
  ) c on c.document_id = d.id
  where d.user_id = auth.uid();

grant select on public.v_user_document_stats to authenticated;

-- v_user_chunk_meta: chunk metadata only (no content, no embedding)
create or replace view public.v_user_chunk_meta
with (security_invoker = true)
as
  select
    dc.id,
    dc.document_id,
    dc.chunk_index,
    dc.section_title,
    dc.heading_level,
    dc.chunk_level,
    dc.token_count
  from public.document_chunks dc
  where dc.user_id = auth.uid();

grant select on public.v_user_chunk_meta to authenticated;

-- v_user_chat_stats: thread/message counts and dates only (no message content)
create or replace view public.v_user_chat_stats
with (security_invoker = true)
as
  select
    count(distinct t.id)::int   as thread_count,
    count(m.id)::int             as message_count,
    max(t.created_at)            as latest_thread_at,
    max(m.created_at)            as latest_message_at
  from public.threads t
  left join public.messages m on m.thread_id = t.id
  where t.user_id = auth.uid();

grant select on public.v_user_chat_stats to authenticated;

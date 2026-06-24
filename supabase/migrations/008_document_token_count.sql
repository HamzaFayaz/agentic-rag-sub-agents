-- Module 8 (A-T1): per-document token total for sub-agent budget routing

alter table public.documents
  add column if not exists total_token_count int;

-- Backfill from existing chunk token_count sums
update public.documents d
set total_token_count = coalesce(
  (
    select sum(dc.token_count)::int
    from public.document_chunks dc
    where dc.document_id = d.id
  ),
  0
)
where d.total_token_count is null;

-- Expose total_token_count in the metadata stats view for SQL/agent reads
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
    d.total_token_count,
    coalesce(c.chunk_count, 0) as chunk_count
  from public.documents d
  left join (
    select document_id, count(*)::int as chunk_count
    from public.document_chunks
    group by document_id
  ) c on c.document_id = d.id
  where d.user_id = auth.uid();

grant select on public.v_user_document_stats to authenticated;

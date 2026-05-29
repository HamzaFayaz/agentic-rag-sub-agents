-- Module 5: chunk structure columns for section-aware / parent-child chunking

-- New columns on document_chunks
alter table public.document_chunks
  add column if not exists section_title text,
  add column if not exists heading_level int,
  add column if not exists parent_id uuid references public.document_chunks (id) on delete set null,
  add column if not exists chunk_level text;

-- Make embedding nullable (parents stored without embedding)
alter table public.document_chunks
  alter column embedding drop not null;

-- Index for parent lookups
create index if not exists document_chunks_parent_id_idx
  on public.document_chunks (parent_id)
  where parent_id is not null;

-- Replace match RPC to return new fields and exclude rows without embedding
-- (Postgres cannot change return type via CREATE OR REPLACE — drop first)
drop function if exists public.match_document_chunks(vector, integer, double precision);

create or replace function public.match_document_chunks(
  query_embedding vector(1536),
  match_count int default 5,
  match_threshold float default 0.7
)
returns table (
  id uuid,
  content text,
  document_id uuid,
  filename text,
  similarity float,
  section_title text,
  heading_level int,
  parent_id uuid,
  chunk_level text
)
language sql
stable
security invoker
set search_path = public
as $$
  select
    dc.id,
    dc.content,
    dc.document_id,
    d.filename,
    1 - (dc.embedding <=> query_embedding) as similarity,
    dc.section_title,
    dc.heading_level,
    dc.parent_id,
    dc.chunk_level
  from public.document_chunks dc
  join public.documents d on d.id = dc.document_id
  where dc.user_id = auth.uid()
    and d.status = 'ready'
    and dc.embedding is not null
    and 1 - (dc.embedding <=> query_embedding) >= match_threshold
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;

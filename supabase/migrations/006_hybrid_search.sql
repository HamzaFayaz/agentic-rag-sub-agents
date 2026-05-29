-- Module 6: hybrid search — full-text search + updated vector RPC
-- Apply in Supabase SQL Editor after 005_chunk_structure.sql
-- Requires: content_tsv tsvector column, GIN index, keyword RPC, updated vector RPC

-- 1. Generated tsvector column for full-text search
alter table public.document_chunks
  add column if not exists content_tsv tsvector
  generated always as (to_tsvector('english', coalesce(content, ''))) stored;

-- 2. GIN index on the tsvector column
create index if not exists document_chunks_content_tsv_gin_idx
  on public.document_chunks using gin (content_tsv);

-- 3. Keyword full-text search RPC (same shape as vector match + section fields)
create or replace function public.match_chunks_keyword(
  query_text text,
  match_count int default 20
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
    ts_rank(dc.content_tsv, plainto_tsquery('english', query_text))::float as similarity,
    dc.section_title,
    dc.heading_level,
    dc.parent_id,
    dc.chunk_level
  from public.document_chunks dc
  join public.documents d on d.id = dc.document_id
  where dc.user_id = auth.uid()
    and d.status = 'ready'
    and dc.embedding is not null
    and dc.content_tsv @@ plainto_tsquery('english', query_text)
  order by similarity desc
  limit match_count;
$$;

-- 4. Updated vector similarity RPC with section fields + embedding filter
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

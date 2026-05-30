-- Module 4: LLM metadata extraction column on documents
-- Apply in Supabase SQL Editor after 002_documents_rag.sql

alter table public.documents
  add column if not exists metadata jsonb not null default '{}';

create index if not exists documents_metadata_doc_type_idx
  on public.documents ((metadata -> 'llm' ->> 'doc_type'));

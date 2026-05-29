-- Module 3: content hash + one filename slot per user (record manager)
-- Apply in Supabase SQL Editor after 002_documents_rag.sql

alter table public.documents
  add column if not exists content_hash text;

create unique index if not exists documents_user_filename_uidx
  on public.documents (user_id, filename);

create index if not exists documents_user_content_hash_idx
  on public.documents (user_id, content_hash);

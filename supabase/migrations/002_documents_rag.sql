-- Module 2: documents, chunks, pgvector, storage RLS, match RPC, message metadata
-- Apply in Supabase SQL Editor (P1-T8)

-- P1-T1: pgvector
create extension if not exists vector;

-- P1-T2: documents
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  filename text not null,
  mime_type text not null,
  storage_path text not null,
  status text not null default 'pending'
    check (status in ('pending', 'processing', 'ready', 'failed')),
  error_message text,
  byte_size bigint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index documents_user_id_created_at_idx
  on public.documents (user_id, created_at desc);

alter table public.documents enable row level security;

create policy "Users can select own documents"
  on public.documents for select
  using (user_id = auth.uid());

create policy "Users can insert own documents"
  on public.documents for insert
  with check (user_id = auth.uid());

create policy "Users can update own documents"
  on public.documents for update
  using (user_id = auth.uid());

create policy "Users can delete own documents"
  on public.documents for delete
  using (user_id = auth.uid());

-- P1-T3: document_chunks
create table public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  chunk_index int not null,
  content text not null,
  embedding vector(1536) not null,
  token_count int,
  created_at timestamptz not null default now()
);

create index document_chunks_document_id_idx
  on public.document_chunks (document_id, chunk_index);

create index document_chunks_embedding_hnsw_idx
  on public.document_chunks
  using hnsw (embedding vector_cosine_ops);

alter table public.document_chunks enable row level security;

create policy "Users can select own document chunks"
  on public.document_chunks for select
  using (user_id = auth.uid());

create policy "Users can insert own document chunks"
  on public.document_chunks for insert
  with check (user_id = auth.uid());

create policy "Users can delete own document chunks"
  on public.document_chunks for delete
  using (user_id = auth.uid());

-- P1-T4: Storage RLS for documents bucket (create bucket in dashboard first)
create policy "Users can read own document files"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users can upload own document files"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users can update own document files"
  on storage.objects for update
  to authenticated
  using (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users can delete own document files"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'documents'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- P1-T5: vector similarity match RPC
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
  similarity float
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
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  join public.documents d on d.id = dc.document_id
  where dc.user_id = auth.uid()
    and d.status = 'ready'
    and 1 - (dc.embedding <=> query_embedding) >= match_threshold
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;

-- P1-T6: message metadata for citations
alter table public.messages
  add column if not exists metadata jsonb not null default '{}';

-- P1-T7: Realtime on documents
alter publication supabase_realtime add table public.documents;

create or replace function public.handle_document_updated_at()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger on_document_update_updated_at
  before update on public.documents
  for each row
  execute function public.handle_document_updated_at();

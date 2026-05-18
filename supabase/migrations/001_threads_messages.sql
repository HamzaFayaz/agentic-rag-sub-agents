-- Module 1: threads + messages with RLS
-- Apply in Supabase SQL Editor (P1-T6)

-- threads
create table public.threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- messages
create table public.messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references public.threads (id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  created_at timestamptz not null default now()
);

create index messages_thread_id_created_at_idx on public.messages (thread_id, created_at);

-- RLS
alter table public.threads enable row level security;
alter table public.messages enable row level security;

create policy "Users can select own threads"
  on public.threads for select
  using (user_id = auth.uid());

create policy "Users can insert own threads"
  on public.threads for insert
  with check (user_id = auth.uid());

create policy "Users can update own threads"
  on public.threads for update
  using (user_id = auth.uid());

create policy "Users can delete own threads"
  on public.threads for delete
  using (user_id = auth.uid());

create policy "Users can select messages in own threads"
  on public.messages for select
  using (
    thread_id in (select id from public.threads where user_id = auth.uid())
  );

create policy "Users can insert messages in own threads"
  on public.messages for insert
  with check (
    thread_id in (select id from public.threads where user_id = auth.uid())
  );

create policy "Users can update messages in own threads"
  on public.messages for update
  using (
    thread_id in (select id from public.threads where user_id = auth.uid())
  );

create policy "Users can delete messages in own threads"
  on public.messages for delete
  using (
    thread_id in (select id from public.threads where user_id = auth.uid())
  );

-- bump threads.updated_at when a message is inserted
create or replace function public.handle_thread_updated_at()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.threads
  set updated_at = now()
  where id = new.thread_id;
  return new;
end;
$$;

create trigger on_message_insert_update_thread
  after insert on public.messages
  for each row
  execute function public.handle_thread_updated_at();

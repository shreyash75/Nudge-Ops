create table if not exists public.investigation_history (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  cluster text,
  status text not null,
  message text,
  investigation jsonb not null default '{}'::jsonb,
  diagnosis jsonb,
  root_cause text,
  namespace text,
  explanation text,
  confidence integer check (confidence between 0 and 100),
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

alter table public.investigation_history
  add column if not exists cluster text,
  add column if not exists root_cause text,
  add column if not exists namespace text,
  add column if not exists explanation text,
  add column if not exists confidence integer;

alter table public.investigation_history enable row level security;

drop policy if exists "users can view own investigations" on public.investigation_history;
create policy "users can view own investigations"
  on public.investigation_history
  for select
  to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "users can insert own investigations" on public.investigation_history;
create policy "users can insert own investigations"
  on public.investigation_history
  for insert
  to authenticated
  with check (user_id = (select auth.uid()));

drop policy if exists "users can update own investigations" on public.investigation_history;
create policy "users can update own investigations"
  on public.investigation_history
  for update
  to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create index if not exists investigation_history_user_created_idx
  on public.investigation_history (user_id, created_at desc);

insert into realtime.channels (pattern, description, enabled)
select 'investigation:%', 'Investigation progress updates', true
where not exists (
  select 1 from realtime.channels where pattern = 'investigation:%'
);

alter table realtime.channels enable row level security;

drop policy if exists "authenticated users can subscribe to investigation channels" on realtime.channels;
create policy "authenticated users can subscribe to investigation channels"
  on realtime.channels
  for select
  to authenticated
  using (pattern = 'investigation:%');

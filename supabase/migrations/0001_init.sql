-- Checkpoint 1: minimal schema, just enough to prove auth + RLS isolation

create table if not exists businesses (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now()
);

alter table businesses enable row level security;

create policy "businesses_owner_select" on businesses
  for select using (owner_id = auth.uid());
create policy "businesses_owner_insert" on businesses
  for insert with check (owner_id = auth.uid());
create policy "businesses_owner_update" on businesses
  for update using (owner_id = auth.uid());
create policy "businesses_owner_delete" on businesses
  for delete using (owner_id = auth.uid());

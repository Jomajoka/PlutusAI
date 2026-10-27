-- Checkpoint 2: catch-all bucket for extracted content that doesn't fit the
-- rigid products/financial_records schema (e.g. competitor mentions, market
-- context, anything else worth keeping for the LLM to reference later).

create table if not exists business_notes (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references businesses (id) on delete cascade,
  -- loose tag for later filtering, e.g. 'competitor', 'market', 'other'. Not
  -- an enum on purpose -- the whole point of this table is not having to
  -- know every category up front.
  category text,
  -- jsonb so this can hold a plain {"text": "..."} note today and something
  -- more structured later without a migration.
  content jsonb not null,
  source_excerpt text,
  created_at timestamptz not null default now()
);

alter table business_notes enable row level security;

create policy "business_notes_owner_select" on business_notes
  for select using (
    exists (select 1 from businesses b where b.id = business_notes.business_id and b.owner_id = auth.uid())
  );
create policy "business_notes_owner_insert" on business_notes
  for insert with check (
    exists (select 1 from businesses b where b.id = business_notes.business_id and b.owner_id = auth.uid())
  );
create policy "business_notes_owner_update" on business_notes
  for update using (
    exists (select 1 from businesses b where b.id = business_notes.business_id and b.owner_id = auth.uid())
  );
create policy "business_notes_owner_delete" on business_notes
  for delete using (
    exists (select 1 from businesses b where b.id = business_notes.business_id and b.owner_id = auth.uid())
  );

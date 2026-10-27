-- Checkpoint 2: minimal schema for ingested data, fields nullable by design
-- (see docs/PROGRESS.md "Schema stays rigid-but-minimal" decision)

create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  business_id uuid not null references businesses (id) on delete cascade,
  name text not null default 'General',
  unit_cost numeric,
  unit_price numeric,
  sourcing_type text check (sourcing_type in ('in_house', 'imported')),
  created_at timestamptz not null default now()
);

create table if not exists financial_records (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products (id) on delete cascade,
  period text,
  revenue numeric,
  units_sold numeric,
  cost_breakdown jsonb,
  -- raw label/snippet the value was matched from, for the confirmation-table UI
  source_excerpt text,
  created_at timestamptz not null default now()
);

alter table products enable row level security;
alter table financial_records enable row level security;

-- products: access via parent business ownership
create policy "products_owner_select" on products
  for select using (
    exists (select 1 from businesses b where b.id = products.business_id and b.owner_id = auth.uid())
  );
create policy "products_owner_insert" on products
  for insert with check (
    exists (select 1 from businesses b where b.id = products.business_id and b.owner_id = auth.uid())
  );
create policy "products_owner_update" on products
  for update using (
    exists (select 1 from businesses b where b.id = products.business_id and b.owner_id = auth.uid())
  );
create policy "products_owner_delete" on products
  for delete using (
    exists (select 1 from businesses b where b.id = products.business_id and b.owner_id = auth.uid())
  );

-- financial_records: access via product -> business ownership
create policy "financial_records_owner_select" on financial_records
  for select using (
    exists (
      select 1 from products p
      join businesses b on b.id = p.business_id
      where p.id = financial_records.product_id and b.owner_id = auth.uid()
    )
  );
create policy "financial_records_owner_insert" on financial_records
  for insert with check (
    exists (
      select 1 from products p
      join businesses b on b.id = p.business_id
      where p.id = financial_records.product_id and b.owner_id = auth.uid()
    )
  );
create policy "financial_records_owner_update" on financial_records
  for update using (
    exists (
      select 1 from products p
      join businesses b on b.id = p.business_id
      where p.id = financial_records.product_id and b.owner_id = auth.uid()
    )
  );
create policy "financial_records_owner_delete" on financial_records
  for delete using (
    exists (
      select 1 from products p
      join businesses b on b.id = p.business_id
      where p.id = financial_records.product_id and b.owner_id = auth.uid()
    )
  );

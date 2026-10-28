-- Cache the LLM-classified industry category on the business itself, so
-- /dashboard/benchmark only pays for one LLM classification call ever (per
-- business), not one per dashboard load. Nullable -- a business with no
-- confident classification yet (or none possible) just has null here, and
-- the backend retries classification on a future load rather than treating
-- null as a permanent "unknown" (see app/classification/industry.py).

alter table businesses add column if not exists industry text;

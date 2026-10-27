# PlutusAI — Build Progress

Tracks checkpoint status for the build. See each checkpoint's section for what was built, verified, and any decisions/gotchas worth remembering.

## Project-wide scoping decisions (set 2026-10-27, before Checkpoint 2)
These came out of a planning discussion about avoiding "just an LLM wrapper that visualizes data" and keeping free-tier-LLM constraints realistic:
- **No vision/multimodal, no OCR.** PDF ingestion is text-layer extraction only (`pdfplumber`/`PyMuPDF`). Scanned/image-only PDFs are out of scope. This also means free-tier text-only LLMs are sufficient — no need for a multimodal model anywhere in the pipeline.
- **Report scope narrowed to standard financial reports** (quarterly/annual filings — e.g. SEC EDGAR 10-K/10-Q, company IR PDFs) rather than arbitrary business documents. These have predictable terminology/structure, which is what makes the keyword/numeric-density page-filtering heuristic viable.
- **CSV/Excel ingestion dropped entirely.** Doesn't match the real use case (small businesses have data in document/report form, not clean spreadsheets) and would have been a third, separate ingestion path for no real benefit. **Text and PDF input are now the only (and core) ingestion modes** — see Checkpoint 2 below. This is a deliberate strength of the system, not just a fallback: the pitch is that it can go through a messy real report and pull out only what's substantial, rather than requiring the user to pre-structure their data.
- **Deterministic-first extraction — the LLM never invents numbers, it only organizes already-extracted ones.** Pipeline, in order:
  1. **Local, deterministic, no LLM, free:** regex/pattern matching over the raw text to pull out candidate (label, value, surrounding context) triples near known financial keywords (e.g. "Revenue: $X", "Units sold: X", currency-adjacent numbers). This is the actual number-extraction step, and it's unit-testable on its own.
  2. **(PDF only) Page filtering first:** before step 1, score pages by keyword hits / numeric density / TOC parsing to shortlist ~10-20 of a 100-200 page report, so step 1 only runs over likely-relevant pages. Not needed for pasted text since it's already short.
  3. **LLM, structuring only:** given the deterministically-extracted candidates (not the raw document), the LLM's job is narrower and safer than "read this and find the numbers" — it maps each candidate to the canonical schema (which field, which product, which period) and resolves terminology (e.g. "turnover"/"sales" → `revenue`, "COGS"/"direct costs" → `cost`). It cannot hallucinate a number that doesn't exist, since it never sees free text to begin with, only pre-extracted candidates.
  4. **Deterministic validation:** the mapped values are still cross-checked against the original extracted candidates (not re-derived from scratch) as a final consistency check.
  5. **User-editable confirmation table** before saving — catches anything genuinely ambiguous or missed.
- **Schema stays rigid-but-minimal, not universal, with explicit fallbacks for variation between businesses:**
  - Canonical schema covers the lowest common denominator the calc engine actually needs (period, revenue, units, cost, product) — not an attempt to model every business's accounting style.
  - Fields are **nullable, not required** — e.g. a business with no per-product breakdown just has a single generic product entry rather than failing to fit.
  - The LLM's structuring step (1.3 above) explicitly includes terminology mapping to the fixed schema field names, rather than the schema trying to grow to match each business's vocabulary.
  - Anything that doesn't map cleanly surfaces in the confirmation table rather than being silently forced into the wrong field.
  - This is honestly scoped as "handles the common case well," not "handles arbitrary business data" — consistent with the proof-of-concept accuracy bar.
- **Demo strategy:** for the live demo, prepare a curated PDF and/or pasted-text sample ourselves that's known to extract well, rather than relying on a random real-world document live on stage. Real messy documents are for showing robustness during development/testing, not for the actual demo moment.
- **Prediction accuracy bar: proof-of-concept, not production-grade.** Naive/simplified assumptions are acceptable and should be shown explicitly (e.g. "elasticity assumed/estimated as X") rather than hidden — honest-naive beats hidden-naive.
- **No training a model on external business datasets.** Rejected due to data availability/overfitting risk vs. a college-project timeline. Worth mentioning as considered-but-deferred future work in the writeup. The per-business elasticity estimation (fit from that business's own historical quarters, see Checkpoint 4 depth additions below) is the scoped-down version of the same idea and is still planned.
- **LLM access is free-tier only, by firm user decision — no paid models.** Mitigations: fallback chain of 2+ free models per task (try A, retry B on failure/timeout) rather than relying on one; deterministic validation + human confirmation table catch quality gaps regardless of model strength; model names kept config-driven (not hardcoded) since free-tier lineups change over time.

## Visualization is a first-class concern, not an afterthought
Agreed during planning: the calc-engine depth additions below are only as impressive as their visualization. Principles for Checkpoint 3 (dashboard) and Checkpoint 5 (scenario results) onward:
- Each feature gets a visual form suited to it, not a generic bar chart: elasticity/sweep optimizer → curve with optimum point highlighted; backtest → predicted-vs-actual comparison view; dashboard → trend (revenue over time) + composition (product mix) charts.
- One consistent color system, chart style, and interaction pattern (tooltips/legends) across the whole app, so it reads as one polished product.
- Recharts is the library; the quality bar comes from deliberate design (color/layout/emphasis) applied when we actually build these, not default chart styling.

## Checkpoint 4 depth additions (to avoid being "just an LLM wrapper")
Agreed during planning, to be built as part of Checkpoint 4 (deterministic calc engine), not Checkpoint 5:
1. **Elasticity estimated from the business's own historical data** (simple regression across their own periods) with fallback to an industry-default constant when there isn't enough historical variation — real statistics, not an LLM guess.
2. **Scenario sweep/optimizer**: sweep a lever (e.g. price) across a range and plot the resulting profit curve, marking the optimum — reframes the product from "answer one question" to "recommend the best move."
3. **Back-test validation**: where a product's history includes a real price/cost change, run the model as if it only knew data before that point and compare its prediction to what actually happened — genuine model validation, strong demo moment.
4. (Lower priority) Side-by-side comparison of multiple scenarios in one view.

## Checkpoint 0 — Skeleton deploy pipeline ✅ Done
- Next.js frontend (Vercel) + FastAPI backend (Render), `/health` endpoint, CORS wired.
- Verified: deployed frontend shows live "Backend status: ok" from the deployed backend.
- Gotcha: `NEXT_PUBLIC_*` env vars are inlined at **build time** on Vercel — adding/changing them requires an actual rebuild (uncheck "Use existing Build Cache" when redeploying), not just a redeploy of the cached build.

## Checkpoint 1 — Auth + minimal schema + manual data entry ✅ Done
- Supabase Auth (email/password) + a single `businesses` table with RLS (`owner_id = auth.uid()`).
- Architecture: frontend uses Supabase Auth directly for login/session; all data CRUD goes through FastAPI, which forwards the user's JWT to Supabase's REST API per-request so RLS enforces isolation (backend never uses the service_role key for this).
- Verified: two test accounts, each creates a business, each only sees their own — confirmed both locally and on the deployed stack.
- Decisions:
  - Schema kept intentionally minimal (just `businesses`) — more tables (`products`, `financial_records`) get added only when a checkpoint actually needs them, not designed upfront.
  - `owner_id` defaults to `auth.uid()` at the DB level, so the backend never needs to decode the JWT itself.
- Bugs hit + fixed:
  - Backend never loaded `.env` locally (no `python-dotenv`) — `SUPABASE_URL` was empty, causing a 500 that surfaced in the browser as a generic "Failed to fetch."
  - `create-next-app`'s generated `.gitignore` blanket-matched `.env*`, silently excluding our `.env.example` files from git — added `!.env*.example` exception.
  - `lib/supabaseClient.ts` created the Supabase client at module-eval time, which crashed the entire Vercel build if env vars were briefly missing — changed to a lazy `getSupabase()` singleton so a missing/misconfigured env var fails at the point of use (in the browser) instead of taking down the whole build.

## `business_notes`: catch-all bucket for anything outside the rigid schema
Added during Checkpoint 2: a `business_notes` table (`category` text tag + `content` jsonb + `source_excerpt`) for content that doesn't fit `products`/`financial_records` — e.g. competitor mentions spotted in a report, market context, anything worth keeping for the LLM to reference later without needing a schema migration every time something new comes up. Scoped by `business_id` with the same RLS ownership pattern as everything else. This gives Checkpoint 6 (competitor lookup) something to read from/write to immediately rather than needing its own new table later.

## Checkpoint 2 — Text + PDF ingestion — Not started
This is the core ingestion checkpoint (CSV/Excel was dropped — see scoping decisions above) and the system's main differentiator: going through messy real documents and extracting only what's substantial, rather than requiring pre-structured input.
- **Build order within this checkpoint:** pasted-text path first (simpler — no page filtering needed), proving the full deterministic-extraction → LLM-structuring → validation → confirmation-table pattern. Then extend to PDF by adding the page-filtering step in front of the same pipeline.
- Will need: `products` / `financial_records` tables, designed now (nullable fields per the schema-flexibility decision above) since this is the checkpoint that actually needs them.
- Deliverable / "done" signal: run both a curated clean sample and a deliberately messy sample (missing fields, unusual terminology) through each path; confirm correct extraction on the clean one and correct *flagging* (not silent wrong data) on the messy one.

## Checkpoint 3 — Dashboard visualization — Not started
- Plan: revenue/product-mix/margin charts (Recharts) reading from real DB records; spot-check against the source document/text by hand.

## Checkpoint 4 — Deterministic calc engine — Not started
- Plan: `simulate_price_change()`, `simulate_sourcing_change()` as pure Python, unit-tested against hand-computed fixtures. No LLM involved. This is the core logic of the project.

## Checkpoint 5 — Scenario query parsing + narration (LLM wired in) — Not started
- Plan: OpenRouter, per-task model routing (strong model for parsing, cheap model for narration). NL query → structured params → calls the tested calc function → narrates the already-computed result.
- **Full pipeline, worked out in planning (example: "what if I increase the price of product X"):**
  1. LLM parses the NL query into structured params only: `{ lever, product_name, magnitude }`. It is given the business's actual product name list as grounding context, so it matches against real names instead of inventing one. The LLM never picks a chart or computes a number — strictly query → params.
  2. Backend resolves `product_name` against the real `products` table itself (exact match, then fuzzy match) — not the LLM's job. If no match or an ambiguous match, return a clarifying response to the frontend (e.g. "did you mean 'Phone Case'?") instead of guessing.
  3. **Missing magnitude is a signal, not an error**: if the user didn't specify an amount ("increase the price" with no number), default to running the Checkpoint 4 sweep/optimizer across a range for that lever, instead of guessing a percentage. If a magnitude was given ("by 10%"), run the single before/after simulation instead. Chosen deterministically by whether `magnitude` parsed as null.
  4. Calc engine runs with basic guardrails (reject/clamp nonsensical magnitudes, e.g. -500%).
  5. **Chart template is selected by which function ran / the output's shape, never decided by the LLM**: sweep output → curve-with-optimum-marked template; single-point output → before/after bars. This mirrors the dashboard's deterministic chart-template approach from Checkpoint 3 planning.
  6. LLM narrates last, off a small summary of the result (e.g. current point + optimum point), not the raw array — and the narration should keep the "this is a simplified/naive estimate" framing visible, per the proof-of-concept accuracy bar.
- **Division of labor, as a standing principle**: the LLM decides *what to compute* (which function, with what params); fixed code decides *what to chart* and *how to validate/resolve* inputs. The LLM is never the source of truth for data matching, chart selection, or the numbers themselves.

## Checkpoint 6 — Competitor lookup (stretch) — Not started
- Plan: on-demand web-search tool call, triggered only when a scenario query references a competitor.

---

## External services status
- GitHub: repo created, pushed.
- Vercel: frontend deployed, env vars set (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
- Render: backend deployed, env vars set (`CORS_ALLOWED_ORIGINS`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`). Free tier sleeps on idle — expect a cold-start delay on first request after inactivity.
- Supabase: project created, `businesses` table + RLS migration applied (`supabase/migrations/0001_init.sql`).
- OpenRouter: not set up yet — needed starting at Checkpoint 2 (text/PDF structuring step), not just Checkpoint 4/5.

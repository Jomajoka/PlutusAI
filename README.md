# PlutusAI — Business Dashboard + What-If Simulator

College major project. Full plan, architecture, module contracts, foundation
rules, and open decisions live in [`docs/implementation-plan.md`](./docs/implementation-plan.md) --
read that first.

## Repo layout

- `frontend/` -- Amplify-hosted React app (upload, dashboard, chat panel, scenario history)
- `backend/lambdas/` -- one folder per Lambda module (ingest_csv, generate_dashboard, chat_agent, run_simulation, dashboard_refresh_trigger)
- `backend/shared/` -- shared DynamoDB/Bedrock helpers and type definitions used across Lambdas
- `infra/` -- AWS CDK app defining every AWS resource (S3, DynamoDB, Lambda, API Gateway, Cognito, EventBridge, Step Functions)
- `tests/` -- per-module tests (start with `run_simulation`)
- `scripts/` -- sample data generation, deploy helper
- `docs/` -- implementation plan and architecture docs

## Getting started

1. Read `docs/implementation-plan.md` (Section 2a "Foundation Rules" is non-negotiable; Section 10 lists what is deliberately still open).
2. Pick a module (see Section 6 for suggested parallel tracks) and work against its documented input/output contract -- other modules can be mocked.
3. `scripts/seed_sample_data.py` gives consistent synthetic test data.

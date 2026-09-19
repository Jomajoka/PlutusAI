"""
Shared type/schema definitions matching docs/implementation-plan.md contracts.
Keep these in sync with the JSON schemas in the plan doc -- this file is the
single source of truth other modules should import from, not re-declare.
"""

# BusinessRecord: { date, product, units_sold, unit_price, unit_cost, extras? (store, channel, ...) }
# ScenarioParams: { scenario_type, params: {...} }
# SimulationResult: {
#   baseline: {revenue, margin, profit},
#   projected: {revenue, margin, profit},
#   series: {metric, x, baseline_y, projected_y},
#   method, assumptions: [str], confidence: "high"|"medium"|"low"
# }
# NOTE: business_id is derived from the Cognito JWT server-side (plan Section 2a);
# it is never taken from the client and never exposed in model-facing tool schemas.

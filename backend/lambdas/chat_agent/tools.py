"""
Tool implementations available to the chat agent.
Each function's signature should match the tool input/output schemas in
docs/implementation-plan.md Module C.
"""

def get_metric(business_id, metric, product=None, date_range=None):
    """Insight-question tool. Reads from BusinessData."""
    raise NotImplementedError

def run_simulation(business_id, scenario_type, params):
    """What-if tool. Invokes Module D (run-simulation Lambda)."""
    raise NotImplementedError

def list_scenarios(business_id, limit=5):
    """Reads from Scenarios table."""
    raise NotImplementedError

TOOL_DEFINITIONS = [
    # Bedrock tool-use JSON schemas for get_metric, run_simulation, list_scenarios
    # go here -- keep in sync with docs/implementation-plan.md Module C.
]

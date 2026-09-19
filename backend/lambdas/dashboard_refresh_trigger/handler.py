"""
Module F -- Background Orchestration glue.
Triggered by EventBridge when new data is uploaded; re-runs Module B.
Lowest priority module -- fine to skip and call generate-dashboard directly
from ingest-csv if short on time (see docs/implementation-plan.md Module F).
"""

def handler(event, context):
    raise NotImplementedError

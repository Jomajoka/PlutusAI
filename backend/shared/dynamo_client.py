"""
Shared DynamoDB helpers used by every Lambda module.
Tables: BusinessData, Scenarios, Users, ConversationSessions (see docs/implementation-plan.md Section 4).
Keep this thin -- one get/put/query helper per table, no business logic here.
"""

def get_business_records(business_id): ...   # -> BusinessData
def put_business_records(business_id, records): ...  # -> BusinessData

def save_scenario(business_id, scenario): ...  # -> Scenarios
def list_scenarios(business_id, limit=5): ...   # -> Scenarios

def get_session_turns(session_id): ...   # -> ConversationSessions
def append_session_turn(session_id, role, content, tool_calls=None): ...  # -> ConversationSessions

"""
Module C -- Chat Agent.
Input:  { session_id, message }   (business_id comes from the verified JWT, NOT the client)
Output: { reply, chart (optional), assumptions (optional), scenario_saved_id (optional) }

Runs a Bedrock tool-calling loop:
  1. Verify the session belongs to the caller's business, then load recent turns
     from ConversationSessions (shared/dynamo_client.py).
  2. Send history + new message + tool definitions (see tools.py) to Bedrock.
     business_id is injected into tool calls here -- it is never in the model's tool schemas.
  3. If Bedrock requests a tool call, execute it (tools.py) and feed the
     result back to Bedrock. Repeat until Bedrock returns final text.
  4. Persist the new turn(s) to ConversationSessions.

The agent must state the simulation's method/assumptions/confidence in its reply.
Transport (streaming vs. polling) is an open decision -- keep payload shapes stable.

See docs/implementation-plan.md Module C for the full contract and tool schemas.
"""

def handler(event, context):
    raise NotImplementedError

def run_agent_loop(business_id, session_id, message):
    raise NotImplementedError

"""
Shared Bedrock invocation helper.
Used by: generate-dashboard (Module B) and chat-agent (Module C).
Wrap model id / region config here so it's set in one place only.
"""

def invoke_model(messages, tools=None, system_prompt=None): ...

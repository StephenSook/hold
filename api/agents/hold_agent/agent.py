"""
The HOLD agent (task 3.1) on google-adk 2.6.3: output_schema and tools together are supported
(structure is enforced on the final output, tools during the thought loop). Runs only behind our
routes through a Runner (api/agents/hold_agent/runner.py); the ADK API server is never mounted.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from api.agents.hold_agent.callbacks import guard_tool_call
from api.agents.hold_agent.prompts import INSTRUCTION
from api.agents.hold_agent.tools import check_legality, lookup_rule, optimize_schedule
from api.hold.config import GEMINI_MODEL
from api.hold.schemas import ExtractResult

root_agent = LlmAgent(
    name="hold_agent",
    model=GEMINI_MODEL,
    description="Turns film production documents into a HOLD schedule and explains child-performer rules from the registry.",
    instruction=INSTRUCTION,
    tools=[check_legality, optimize_schedule, lookup_rule],
    output_schema=ExtractResult,
    before_tool_callback=guard_tool_call,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

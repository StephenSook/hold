"""
The HOLD agents (task 3.1) on google-adk 2.6.3. Two agents, because on gemini-3.1-flash-lite an
agent with tools AND an output_schema never emits its final structured answer: traced live
(task 3.4), it re-called lookup_rule with the same arguments after a correct result, then kept
calling through the budget refusals until the ADK call ceiling. Without the schema the same
agent answers in three events. So the tool-bearing agent answers free-form and the tool-less
extraction twin carries the schema. Both run only behind our routes through a Runner
(api/agents/hold_agent/runner.py); the ADK API server is never mounted.
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
    before_tool_callback=guard_tool_call,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# Extraction never calls a tool (a human confirms before anything is solved), so the extraction
# route runs this tool-less twin: one structured answer per request, the schema enforced.
extract_agent = LlmAgent(
    name="hold_extract",
    model=GEMINI_MODEL,
    description="Turns one film production document into a HOLD ExtractResult, with no tools.",
    instruction=INSTRUCTION,
    tools=[],
    output_schema=ExtractResult,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

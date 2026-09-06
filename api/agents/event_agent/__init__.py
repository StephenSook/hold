"""
The event interpreter as its own ADK agent module (task 3.4, second eval set).

`adk eval <dir> <evalset>` evaluates the module's `root_agent`, so an agent that is a sibling of
`root_agent` inside another package cannot be evaluated by pointing at that package: the run would
score the tool-bearing agent against answers only the interpreter can give. This module exists so
the interpreter has an eval of its own rather than an eval of its neighbour.

There is one definition of the agent, in api.agents.hold_agent.agent, and this re-exports it. A
second construction here would be a second agent that happens to look like the deployed one, and
the eval would then be evidence about a copy.
"""
from api.agents.hold_agent.agent import event_agent as root_agent

__all__ = ["root_agent"]

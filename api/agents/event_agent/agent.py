"""ADK looks for `agent.root_agent` when a module is given as a directory. Same one object."""
from api.agents.hold_agent.agent import event_agent as root_agent

__all__ = ["root_agent"]

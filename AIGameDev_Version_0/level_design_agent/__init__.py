from .agent import root_agent

# Export the agent for ADK to find
__all__ = ['root_agent']
agent = root_agent
__all__ = ['root_agent', 'agent']
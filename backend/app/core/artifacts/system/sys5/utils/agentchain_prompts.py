"""
Utility to fetch prompts from agentchain in state.

Agentchain is passed as a list of agent configurations:
[
    {"agent_name": "generation_agent", "agent_version": "V1.0", "prompt_content": "..."},
    {"agent_name": "verification_agent", "agent_version": "V1.0", "prompt_content": "..."},
    {"agent_name": "qa_agent", "agent_version": "V1.0", "prompt_content": "..."},
    ...
]
"""

from typing import List, Dict, Any, Optional


def get_prompt_from_agentchain(
    agentchain: List[Dict[str, Any]],
    agent_name: str,
    default: Optional[str] = None
) -> Optional[str]:
    """
    Get prompt content from agentchain list.

    Args:
        agentchain: List of agent configurations from state
        agent_name: Name of agent to find (e.g., "generation_agent", "verification_agent")
        default: Default prompt if agent not found

    Returns:
        Prompt content string or default if not found
    """
    if not agentchain:
        return default

    for agent in agentchain:
        if isinstance(agent, dict) and agent.get("agent_name") == agent_name:
            prompt = agent.get("prompt_content")
            if prompt:
                return prompt
            else:
                # Agent found but prompt_content is empty - log this
                import sys
                print(f"[DEBUG] Agent '{agent_name}' found but prompt_content is empty/null", file=sys.stderr)
                print(f"[DEBUG] Agent keys: {list(agent.keys())}", file=sys.stderr)
                return default

    return default


def get_all_agents_from_agentchain(
    agentchain: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Get all agents from agentchain as a dict keyed by agent_name.

    Args:
        agentchain: List of agent configurations from state

    Returns:
        Dict mapping agent_name -> {agent_version, prompt_content, ...}
    """
    if not agentchain:
        return {}

    return {
        agent.get("agent_name", ""): agent
        for agent in agentchain
        if isinstance(agent, dict) and agent.get("agent_name")
    }

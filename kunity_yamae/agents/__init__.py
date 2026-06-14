from .base import BaseAgent
from .local_patch_agent import LocalPatchAgent

AGENT_REGISTRY = {
    "local-patch": LocalPatchAgent,
}


def get_agent(name: str, config: dict) -> BaseAgent:
    """Get an agent instance by name."""
    agent_cls = AGENT_REGISTRY.get(name)
    if not agent_cls:
        raise ValueError(f"Unknown agent: {name}. Available: {list(AGENT_REGISTRY.keys())}")
    agent_config = config.get("agents", {}).get("backends", {}).get(name, {})
    return agent_cls(name, config, agent_config)


def list_agents() -> list[str]:
    return list(AGENT_REGISTRY.keys())

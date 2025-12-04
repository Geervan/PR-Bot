from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, context: Dict[str, Any]):
        self.context = context

    @abstractmethod
    async def run(self) -> Any:
        """Executes the agent's main logic."""
        pass

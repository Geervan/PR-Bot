import time
from typing import List, Optional
from app.core.config import settings

class KeyManager:
    def __init__(self):
        self.keys: List[str] = settings.api_keys
        self.current_index: int = 0
        self.cooldowns: dict[str, float] = {}  # key -> timestamp when it becomes available
        self.COOLDOWN_DURATION = 60.0  # seconds

    def get_next_key(self) -> Optional[str]:
        """Returns the next available key using round-robin strategy."""
        if not self.keys:
            return None

        start_index = self.current_index
        while True:
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)

            if self._is_key_ready(key):
                return key

            # If we've cycled through all keys and none are ready
            if self.current_index == start_index:
                print("Warning: All API keys are currently cooling down.")
                # Fallback: return the one with the shortest remaining cooldown or just the next one
                # For now, let's just return the next one and hope for the best, 
                # or we could implement a wait.
                return key

    def _is_key_ready(self, key: str) -> bool:
        """Checks if a key is past its cooldown period."""
        if key not in self.cooldowns:
            return True
        if time.time() > self.cooldowns[key]:
            del self.cooldowns[key]
            return True
        return False

    def report_rate_limit(self, key: str):
        """Marks a key as rate-limited."""
        print(f"Rate limit reported for key ending in ...{key[-4:]}. Cooling down for {self.COOLDOWN_DURATION}s.")
        self.cooldowns[key] = time.time() + self.COOLDOWN_DURATION

key_manager = KeyManager()

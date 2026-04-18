from collections import deque
from typing import List, Any, Optional
import random

from hsci.core.data_types import Episode, PerceptionMap
from hsci.core.config import SystemConfig

class EpisodeMemory:
    """
    Stores past problem-solving episodes.
    Uses a deque to maintain a fixed-size memory of the most recent episodes.
    """

    def __init__(self, max_episodes: Optional[int] = None):
        self.config = SystemConfig()
        self.max_episodes = max_episodes if max_episodes is not None else self.config.episode_memory_max_episodes
        self.memory: deque[Episode] = deque(maxlen=self.max_episodes)

    def store(self, episode: Episode):
        """Stores a new episode in memory."""
        self.memory.append(episode)

    def find_similar(self, perception: PerceptionMap, top_k: int = 3) -> List[Episode]:
        """
        Placeholder for finding similar past episodes.
        In a full implementation, this would involve comparing the input perception
        to stored episode inputs using embeddings or structural matching.
        For now, it returns a random sample of stored episodes.
        """
        if not self.memory:
            return []
        
        # Return a random sample as a placeholder for "similar" episodes
        return random.sample(list(self.memory), min(top_k, len(self.memory)))
    
    def get_all_episodes(self) -> List[Episode]:
        """Returns all episodes currently stored in memory."""
        return list(self.memory)

    def clear(self):
        """Clears all episodes from memory."""
        self.memory.clear()
from collections import deque
import pytest
from datetime import datetime, timedelta
from hsci.core.data_types import Episode, PerceptionMap, InputSignal, Expression, ProofTrace, AxiomType, PerceiverConfig
from hsci.knowledge.episode_memory import EpisodeMemory
from hsci.core.config import SystemConfig

@pytest.fixture
def system_config():
    return SystemConfig()

@pytest.fixture
def episode_memory(system_config):
    return EpisodeMemory(max_episodes=system_config.episode_memory_max_episodes)

@pytest.fixture
def sample_episodes():
    episodes = []
    for i in range(10):
        input_signal = InputSignal(
            raw_text=f"problem {i}",
            structured_data=None,
            timestamp=datetime.now() - timedelta(seconds=i),
            session_id=f"session_{i}"
        )
        perception = PerceptionMap(
            entities={f"var{i}": i},
            unknown_entities=[],
            relationships=[],
            intent=AxiomType.REDUCTION,
            confidence=0.8,
            entity_graph={"nodes": [f"var{i}"]}
        )
        solution = Expression(value=i*2, concepts_used=["dummy_concept"])
        proof = ProofTrace(
            steps=[f"step {i}"],
            variables={f"var{i}": i},
            concepts_applied=["dummy_concept"],
            structural_pattern="dummy_pattern"
        )
        episode = Episode(
            input=perception,
            solution=solution,
            proof=proof,
            concepts_used=["dummy_concept"],
            timestamp=datetime.now() - timedelta(seconds=i)
        )
        episodes.append(episode)
    return episodes

def test_store_episode(episode_memory, sample_episodes):
    episode = sample_episodes[0]
    episode_memory.store(episode)
    assert len(episode_memory.memory) == 1
    assert episode_memory.memory[0] == episode

def test_max_episodes_limit(episode_memory):
    # Set a small max_episodes for testing
    episode_memory.max_episodes = 3
    episode_memory.memory = deque(maxlen=3) # Reset deque with new maxlen

    ep1 = Episode(input=None, solution=None, proof=None, concepts_used=[], timestamp=datetime.now())
    ep2 = Episode(input=None, solution=None, proof=None, concepts_used=[], timestamp=datetime.now())
    ep3 = Episode(input=None, solution=None, proof=None, concepts_used=[], timestamp=datetime.now())
    ep4 = Episode(input=None, solution=None, proof=None, concepts_used=[], timestamp=datetime.now())

    episode_memory.store(ep1)
    episode_memory.store(ep2)
    episode_memory.store(ep3)
    assert len(episode_memory.memory) == 3
    assert episode_memory.memory[0] == ep1

    episode_memory.store(ep4)
    assert len(episode_memory.memory) == 3
    assert episode_memory.memory[0] == ep2 # Oldest episode (ep1) should be removed

def test_get_all_episodes(episode_memory, sample_episodes):
    for ep in sample_episodes[:5]:
        episode_memory.store(ep)
    
    all_episodes = episode_memory.get_all_episodes()
    assert len(all_episodes) == 5
    assert all(isinstance(ep, Episode) for ep in all_episodes)

def test_clear_episodes(episode_memory, sample_episodes):
    for ep in sample_episodes[:3]:
        episode_memory.store(ep)
    assert len(episode_memory.memory) == 3
    
    episode_memory.clear()
    assert len(episode_memory.memory) == 0

def test_find_similar_empty_memory(episode_memory):
    perception = PerceptionMap(
        entities={}, unknown_entities=[], relationships=[], intent=AxiomType.REDUCTION, confidence=0.0, entity_graph=None
    )
    similar_episodes = episode_memory.find_similar(perception)
    assert similar_episodes == []

def test_find_similar_returns_random_sample(episode_memory, sample_episodes):
    for ep in sample_episodes:
        episode_memory.store(ep)
    
    perception = PerceptionMap(
        entities={"x": 10}, unknown_entities=[], relationships=[], intent=AxiomType.REDUCTION, confidence=0.0, entity_graph=None
    )
    
    # Test top_k less than total episodes
    similar_episodes = episode_memory.find_similar(perception, top_k=3)
    assert len(similar_episodes) == 3
    assert all(isinstance(ep, Episode) for ep in similar_episodes)
    
    # Test top_k greater than total episodes
    similar_episodes_all = episode_memory.find_similar(perception, top_k=20)
    assert len(similar_episodes_all) == len(sample_episodes)

    # Check if a different random sample is returned on subsequent calls
    similar_episodes_1 = episode_memory.find_similar(perception, top_k=5)
    similar_episodes_2 = episode_memory.find_similar(perception, top_k=5)
    # This might fail rarely due to true randomness, but generally should be different
    # assert similar_episodes_1 != similar_episodes_2 # Not a strong assertion, just for understanding

from dataclasses import dataclass, field

@dataclass
class PerceiverConfig:
    input_dim: int = 256
    hidden_dim: int = 512
    output_dim: int = 128
    num_layers: int = 4

@dataclass
class SystemConfig:
    # Z3 Verification Engine
    z3_timeout_ms: int = 5000

    # Neural Perceiver
    perceiver_config: PerceiverConfig = field(default_factory=PerceiverConfig)
    
    # Knowledge Base
    episode_memory_max_episodes: int = 10000

    # Reasoning Engine
    reasoning_max_attempts: int = 5

    # Learning Engine
    learning_rate: float = 0.01
    weakening_factor: float = 0.1 # Used when learning from counterexamples

    # Self-Play Engine
    self_play_sleep_time_s: float = 0.1
    self_play_weak_concept_target_n: int = 3

    # General System
    log_level: str = "INFO"

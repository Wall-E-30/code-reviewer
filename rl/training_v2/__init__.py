"""
rl/training_v2

Training v2 on Real Signal subsystem (Phase 11):
- Real signal data mixer with strict <= 50% synthetic cap (TRAIN2-01)
- Test-verified LLM bug generator with distinct training/eval sources (TRAIN2-02)
- Anti-reward-hacking audits v2 & RewardVersion tracking (TRAIN2-03)
- Ablation configurations, notebooks & runner (TRAIN2-04)
"""

from rl.training_v2.data_mixer import DataMixer, TrainingItem, StreamType

__all__ = [
    "DataMixer",
    "TrainingItem",
    "StreamType",
]


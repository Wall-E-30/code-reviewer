"""
rl/training/config.py

Hyperparameter and execution configuration for Aion code model training (TRAIN-01).
Supports QLoRA 4-bit, standard LoRA, and dry-run execution on CPU/test runners.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrainingConfig:
    """Configuration dataclass for model training pipelines (SFT, RLVR)."""

    base_model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    learning_rate: float = 2e-4
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    num_train_epochs: int = 3
    warmup_ratio: float = 0.05
    weight_decay: float = 0.01
    logging_steps: int = 10
    save_steps: int = 100
    device: str = "auto"
    fp16: bool = True
    dry_run: bool = False
    max_samples: Optional[int] = None
    output_dir: str = "models/sft_output"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TrainingConfig:
        """Instantiate configuration from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


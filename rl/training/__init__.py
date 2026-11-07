"""
rl/training package.
Provides SFT warm-start, actionability verifier modeling, GRPO policy optimization,
and model quantization for Aion Code Reviewer.
"""

from rl.training.bootstrap_eval import BootstrapEvaluator
from rl.training.config import TrainingConfig
from rl.training.formatter import ChatMLFormatter
from rl.training.grpo import GRPOConfig, GRPOTrainer, ReviewTrajectory, compute_group_advantages
from rl.training.quantize import ModelQuantizer
from rl.training.sft import SFTWarmStartTrainer
from rl.training.verifier_model import (
    ActionabilityDatasetBuilder,
    ActionabilityFeatureExtractor,
    ActionabilityVerifierModel,
    TemperatureCalibrator,
)

__all__ = [
    "TrainingConfig",
    "ChatMLFormatter",
    "SFTWarmStartTrainer",
    "ActionabilityDatasetBuilder",
    "ActionabilityFeatureExtractor",
    "ActionabilityVerifierModel",
    "TemperatureCalibrator",
    "GRPOConfig",
    "GRPOTrainer",
    "ReviewTrajectory",
    "compute_group_advantages",
    "BootstrapEvaluator",
    "ModelQuantizer",
]

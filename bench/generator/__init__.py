"""
bench/generator

Synthetic bug injection, clean negative diff generation, and corpus synthesis
for the Aion-Bench evaluation suite (BENCH-02).
"""

from bench.generator.clean import CleanDiffGenerator
from bench.generator.injector import BugInjector

__all__ = ["BugInjector", "CleanDiffGenerator"]

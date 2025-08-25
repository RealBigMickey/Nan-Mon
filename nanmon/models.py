from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

KINDS = ["DORITOS", "BURGERS", "FRIES", "ICECREAM", "SODA", "CAKE"]

@dataclass
class EatenCounters:
    # Total foods eaten (correct + wrong)
    total: int = 0
    # Correct foods eaten
    correct: int = 0
    # Per-type counts
    per_type: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in KINDS})

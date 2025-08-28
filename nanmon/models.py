from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

KINDS = [
    # Level 1
    "DORITOS", "BURGERS", "FRIES", "ICECREAM", "SODA", "CAKE",
    # Level 2
    "SHAVEDICE", "DONUT", "CUPCAKE", "RIBS", "HOTDOG", "FRIEDCHICKEN",
    # HOTDOG split parts
    "DOG", "BREAD",
    # Level 3
    "BEEFSOUP", "RICEBOWLCAKE", "TAINANPORRIDGE", "TAINANPUDDING", "TOFUPUDDING", "TAINANTOFUICE",
]
@dataclass
class EatenCounters:
    # Total foods eaten (correct + wrong)
    total: int = 0
    # Correct foods eaten
    correct: int = 0
    # Per-type counts
    per_type: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in KINDS})

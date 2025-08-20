from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

KINDS = ["DORITOS", "BURGERS", "FRIES", "ICECREAM", "SODA", "CAKE"]

@dataclass
class EatenCounters:
    total: int = 0
    per_type: Dict[str, int] = None

    def __post_init__(self):
        if self.per_type is None:
            self.per_type = {k: 0 for k in KINDS}

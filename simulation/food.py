"""Food — the resource organisms compete for."""

from dataclasses import dataclass


@dataclass(slots=True)
class Food:
    id: int
    x: float
    y: float
    energy: float

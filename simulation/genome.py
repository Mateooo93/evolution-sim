"""Heritable traits: the genome and its mapping to visible phenotypes.

Every trait is a float in [0, 1]. Higher is not always better — each
trait carries a tradeoff enforced in `energy_drain_per_s` and friends.

Wired into the simulation right now: speed, size, metabolism, lifespan,
efficiency. Still dormant (activated by later milestones):
vision (sensing), fertility (reproduction), aggression (predation).
"""

import random
from dataclasses import dataclass

TRAIT_NAMES = (
    "speed",
    "size",
    "vision",
    "metabolism",
    "fertility",
    "lifespan",
    "aggression",
    "efficiency",
)


@dataclass(slots=True)
class Genome:
    speed: float  # faster movement, higher movement upkeep
    size: float  # bigger body, higher upkeep, bigger target
    vision: float  # sensing range (food/predators) — dormant
    metabolism: float  # base energy burn rate
    fertility: float  # reproduction readiness — dormant
    lifespan: float  # max age in seconds
    aggression: float  # predator behavior — dormant
    efficiency: float  # lowers every energy cost


def random_genome() -> Genome:
    return Genome(*(random.random() for _ in TRAIT_NAMES))


# --- phenotype mapping (pure geometry) --------------------------------

def body_radius_px(size: float) -> float:
    return 2.0 + size * 6.0  # 2..8 px


def move_speed_px(genome: Genome) -> float:
    return 10.0 + genome.speed * 60.0  # 10..70 px/s

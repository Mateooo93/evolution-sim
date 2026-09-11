"""Heritable traits: the genome and its mapping to visible phenotypes.

Every trait is a float in [0, 1]. Higher is not always better — each
trait carries a tradeoff enforced in `energy_drain_per_s` and friends.

Wired into the simulation right now: speed, size, metabolism, lifespan,
efficiency, vision (sensing), fertility (reproduction). Still dormant:
aggression (predation).
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


# --- genetics --------------------------------------------------------

def crossover(a: Genome, b: Genome) -> Genome:
    """Uniform crossover: each trait is copied from a random parent."""
    return Genome(
        **{n: random.choice((getattr(a, n), getattr(b, n))) for n in TRAIT_NAMES}
    )


def mutate(g: Genome, rate: float) -> Genome:
    """Per-trait point mutation: with probability `rate`, nudge the trait.

    The nudge is a Gaussian step clamped to [0, 1]. `rate` is the
    probability per trait (the user-facing mutation slider).
    """
    if rate <= 0.0:
        return g
    vals = {}
    for n in TRAIT_NAMES:
        v = getattr(g, n)
        if random.random() < rate:
            v = max(0.0, min(1.0, v + random.gauss(0.0, 0.15)))
        vals[n] = v
    return Genome(**vals)


# --- phenotype mapping (pure geometry) --------------------------------

def body_radius_px(size: float) -> float:
    return 2.0 + size * 6.0  # 2..8 px


def move_speed_px(genome: Genome) -> float:
    return 10.0 + genome.speed * 60.0  # 10..70 px/s

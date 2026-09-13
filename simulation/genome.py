"""Heritable traits: the genome and its mapping to visible phenotypes.

Every trait is a float in [0, 1]. Higher is not always better — each
trait carries a tradeoff enforced in `Ecosystem._drain` and friends.

All eight traits are live: speed and size set how a body moves and what
it costs, vision sets sensing range, metabolism and efficiency set the
burn, fertility sets breeding readiness, lifespan sets the age limit,
and aggression splits the population between foragers and hunters.
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


# Where the aggression spectrum divides into readable roles. These are
# labels for the UI only — behaviour is continuous.
PREY_MAX = 0.35
PREDATOR_MIN = 0.70


def role_of(aggression: float) -> str:
    """'prey' | 'mixed' | 'predator' — a display label for a trait value."""
    if aggression >= PREDATOR_MIN:
        return "predator"
    if aggression >= PREY_MAX:
        return "mixed"
    return "prey"


@dataclass(slots=True)
class Genome:
    speed: float  # faster movement, higher movement upkeep
    size: float  # bigger body, higher upkeep, easier to spot
    vision: float  # sensing range for food and neighbours
    metabolism: float  # base energy burn rate
    fertility: float  # how fast breeding readiness accumulates
    lifespan: float  # max age in seconds
    aggression: float  # hunt-vs-forage split (predator behaviour)
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

# the genome. 8 traits, all floats 0..1, nothing else to it.
# higher isnt always better, every trait has a cost somewhere in ecosystem.py

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

# where we draw the line between "prey" / "mixed" / "predator" in the UI.
# its only a label, the actual behaviour is a smooth 0..1 thing
PREY_MAX = 0.35
PREDATOR_MIN = 0.70


def role_of(aggression: float) -> str:
    if aggression >= PREDATOR_MIN:
        return "predator"
    if aggression >= PREY_MAX:
        return "mixed"
    return "prey"


@dataclass(slots=True)
class Genome:
    speed: float        # faster but burns more
    size: float         # bigger body, more upkeep
    vision: float       # how far it can see food + other creatures
    metabolism: float   # base burn rate
    fertility: float    # how fast it gets ready to breed
    lifespan: float     # max age
    aggression: float   # hunt vs forage split
    efficiency: float   # discount on all the energy costs


def random_genome() -> Genome:
    # just 8 random numbers, the founders are meant to be bad at everything
    return Genome(*(random.random() for _ in TRAIT_NAMES))


def crossover(a: Genome, b: Genome) -> Genome:
    # coin flip per trait, so a kid can get dads speed and mums eyes etc
    return Genome(
        **{n: random.choice((getattr(a, n), getattr(b, n))) for n in TRAIT_NAMES}
    )


def mutate(g: Genome, rate: float) -> Genome:
    # each trait gets a small gaussian kick with probability = rate.
    # 0.15 looked about right, bigger and everything just becomes noise
    if rate <= 0.0:
        return g
    vals = {}
    for n in TRAIT_NAMES:
        old = getattr(g, n)  # keep a copy around, handy when debugging
        v = old
        if random.random() < rate:
            v = max(0.0, min(1.0, v + random.gauss(0.0, 0.15)))
        vals[n] = v
    return Genome(**vals)


# traits to real numbers

def body_radius_px(size: float) -> float:
    return 2.0 + size * 6.0  # 2..8 px


def move_speed_px(genome: Genome) -> float:
    return 10.0 + genome.speed * 60.0  # 10..70 px/s

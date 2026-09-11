from dataclasses import dataclass

from .food import Food
from .genome import Genome


@dataclass(slots=True)
class Organism:
    """A living organism with a heritable genome.

    Energy drains every tick (metabolism + movement + body upkeep);
    hitting zero means starvation death. Ageing past the genome's
    lifespan means natural death.
    """

    id: int
    x: float
    y: float
    heading: float  # movement direction in radians
    genome: Genome
    energy: float
    age: float
    generation: int = 1  # genealogical generation (initial stock is 1)
    readiness: float = 0.0  # accumulates to 1.0, gated by fertility
    target: Food | None = None  # food currently being chased
    last_sense: float = 0.0  # sim time of the last food scan
    # Predation:
    dead: bool = False  # flagged when removed by any cause (swept each tick)
    prey_target: "Organism | None" = None  # prey being hunted (predators only)
    last_hunt: float = 0.0  # sim time of the last prey scan
    danger: "Organism | None" = None  # nearest threat sensed (higher aggression)
    fleeing: bool = False  # sprinting away this tick (resets each tick)
    on_hunt: bool = False  # hunting this hunger span (aggression-weighted)

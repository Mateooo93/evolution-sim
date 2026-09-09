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
    target: Food | None = None  # food currently being chased
    last_sense: float = 0.0  # sim time of the last food scan

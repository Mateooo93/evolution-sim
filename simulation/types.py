from dataclasses import dataclass


@dataclass(slots=True)
class Organism:
    """An organism in the simulation.

    Foundation stage: just a moving dot with a heading.
    Later milestones add: genome, energy, age, sensors, species color...
    """

    id: int
    x: float
    y: float
    heading: float  # movement direction in radians

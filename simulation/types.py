# a creature. mostly plain data, the actual thinking happens in ecosystem.py

from dataclasses import dataclass

from .food import Food
from .genome import Genome


@dataclass(slots=True)
class Organism:
    id: int
    x: float
    y: float
    heading: float  # radians, where its pointing
    genome: Genome
    energy: float
    age: float
    generation: int = 1  # founders are gen 1
    readiness: float = 0.0  # creeps up to 1.0 then it can breed
    target: Food | None = None  # the food its chasing rn
    last_sense: float = 0.0  # last time we did a food scan
    # predation stuff
    dead: bool = False  # gets flagged, cleaned up at the end of the tick
    prey_target: "Organism | None" = None
    last_hunt: float = 0.0
    danger: "Organism | None" = None  # something scarier nearby
    fleeing: bool = False  # set every tick while running away
    hunting: bool = False  # set every tick while chasing
    on_hunt: bool = False  # committed to hunting for a while
    role_until: float = 0.0  # ...until this time
    chase_started: float = 0.0  # so we can give up on hopeless chases
    # family tree. lineage = id of the founder this one came from, so the
    # whole family shares one number
    lineage: int = 0
    parent_a: int | None = None
    parent_b: int | None = None
    born_at: float = 0.0


@dataclass(slots=True)
class Event:
    # "something happened" messages for the drawing code, so the sim itself
    # stays headless and doesnt know about rings/pulses/log lines
    t: float
    kind: str  # 'birth' | 'ate' | 'starved' | 'aged' | 'eaten' | 'arrived'
    x: float
    y: float
    actor: int  # who it happened to
    other: int = 0  # who did it (the predator on an 'eaten', the parent on a 'birth')

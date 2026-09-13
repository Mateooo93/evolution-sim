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
    hunting: bool = False  # chasing prey this tick (resets each tick)
    on_hunt: bool = False  # hunting this hunger span (aggression-weighted)
    role_until: float = 0.0  # sim time the current role commitment expires
    chase_started: float = 0.0  # sim time the current chase began
    # --- descent ---------------------------------------------------------
    # The family line: every organism carries the id of the founder it
    # descends from, inherited from its first parent. Line members are the
    # "kin" the plate highlights when you select one of them.
    lineage: int = 0
    parent_a: int | None = None  # first parent (the one lineage comes from)
    parent_b: int | None = None  # second parent
    born_at: float = 0.0  # sim time of birth (0 for the founding stock)


@dataclass(slots=True)
class Event:
    """One thing that happened in the world, for the view layers to read.

    The simulation stays headless: it emits what happened and where, and
    the renderer / HUD decide whether anything should be drawn or logged.
    """

    t: float  # sim time
    kind: str  # 'birth' | 'mate' | 'ate' | 'starved' | 'aged' | 'eaten'
    x: float
    y: float
    actor: int  # organism the event is about
    other: int = 0  # who caused it (predator on 'eaten', parent on 'birth')

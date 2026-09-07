"""EvoLab — artificial ecosystem simulator."""

import math
import random
from dataclasses import dataclass

from .genome import Genome, move_speed_px, random_genome
from .types import Organism


@dataclass
class WorldConfig:
    width: int
    height: int
    organisms: int  # starting organism count
    wander_turn_rate: float  # how eagerly a creature changes direction (rad/s)

    # --- energy ---------------------------------------------------------
    max_energy: float = 100.0
    base_metabolism: float = 0.10  # energy/s at minimal traits
    metabolism_range: float = 0.40  # extra burn from the metabolism trait
    speed_cost: float = 0.6  # upkeep multiplier weight for speed trait
    size_cost: float = 0.8  # upkeep multiplier weight for size trait
    efficiency_saving: float = 0.5  # fraction of upkeep efficiency can erase

    # --- life ------------------------------------------------------------
    base_lifespan: float = 120.0  # seconds at lifespan trait 0
    lifespan_range: float = 480.0  # extra seconds at lifespan trait 1

    # --- immigration -----------------------------------------------------
    # Until food + reproduction land (next milestones), a slow stream of
    # fresh random immigrants keeps the lab population from emptying out
    # once starvation/age kill off the initial stock. Replaced by real
    # births later.
    min_population: int = 40
    migration_rate: float = 1.0  # immigrants per second while below floor


class Ecosystem:
    """All simulation state. No rendering, no pygame, no UI.

    The only thing an ecosystem knows how to do is advance by `dt` seconds.
    The UI owns the clock and calls `update`.
    """

    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.organisms: list[Organism] = []
        self.time = 0.0  # simulation time in seconds
        self.deaths: dict[str, int] = {"starvation": 0, "age": 0}
        self._next_id = 1
        self._migration_acc = 0.0
        for _ in range(config.organisms):
            self._spawn()

    # --- population -----------------------------------------------------

    def _spawn(self) -> None:
        c = self.config
        self.organisms.append(
            Organism(
                id=self._next_id,
                x=random.random() * c.width,
                y=random.random() * c.height,
                heading=random.random() * 2 * math.pi,
                genome=random_genome(),
                energy=c.max_energy,
                age=0.0,
            )
        )
        self._next_id += 1

    def _kill(self, o: Organism, cause: str) -> None:
        self.organisms.remove(o)
        self.deaths[cause] = self.deaths.get(cause, 0) + 1

    # --- behaviour ------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the simulation by `dt` seconds."""
        self.time += dt
        c = self.config

        for o in list(self.organisms):
            o.age += dt

            # Wander: continuously drift the heading by a random amount.
            # This will be replaced by real behavior (seek food / flee
            # predator) once organisms have senses.
            o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt

            o.x += math.cos(o.heading) * move_speed_px(o.genome) * dt
            o.y += math.sin(o.heading) * move_speed_px(o.genome) * dt

            # Toroidal world: wrap around the edges instead of hitting walls.
            self._wrap(o)

            o.energy = max(0.0, o.energy - self._drain(o.genome) * dt)
            if o.energy <= 0.0:
                self._kill(o, "starvation")
            elif o.age >= self._max_age(o.genome):
                self._kill(o, "age")

        self._migrate(dt)

    def _migrate(self, dt: float) -> None:
        c = self.config
        if len(self.organisms) >= c.min_population:
            self._migration_acc = 0.0
            return
        self._migration_acc += dt * c.migration_rate
        while self._migration_acc >= 1.0 and len(self.organisms) < c.min_population:
            self._migration_acc -= 1.0
            self._spawn()

    # --- trait costs -----------------------------------------------------

    def _drain(self, g: Genome) -> float:
        """Energy per second: metabolism × movement/body upkeep − efficiency."""
        c = self.config
        metabolism = c.base_metabolism + g.metabolism * c.metabolism_range
        upkeep = 1.0 + g.speed * c.speed_cost + g.size * c.size_cost
        saving = 1.0 - g.efficiency * c.efficiency_saving
        return metabolism * upkeep * saving

    def _max_age(self, g: Genome) -> float:
        c = self.config
        return c.base_lifespan + g.lifespan * c.lifespan_range

    # --- observations ----------------------------------------------------

    def trait_average(self, trait: str) -> float:
        """Average of a genome trait across the population, or 0 if empty."""
        pop = self.organisms
        if not pop:
            return 0.0
        return sum(getattr(o.genome, trait) for o in pop) / len(pop)

    # --- helpers ----------------------------------------------------------

    def _wrap(self, o: Organism) -> None:
        c = self.config
        if o.x < 0:
            o.x += c.width
        elif o.x >= c.width:
            o.x -= c.width
        if o.y < 0:
            o.y += c.height
        elif o.y >= c.height:
            o.y -= c.height

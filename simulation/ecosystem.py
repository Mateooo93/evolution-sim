"""EvoLab — artificial ecosystem simulator."""

import math
import random
from dataclasses import dataclass

from .types import Organism


@dataclass
class WorldConfig:
    width: int
    height: int
    organisms: int  # starting organism count
    speed: float  # movement speed in pixels/second
    wander_turn_rate: float  # how eagerly a creature changes direction (rad/s)


class Ecosystem:
    """All simulation state. No rendering, no pygame, no UI.

    The only thing an ecosystem knows how to do is advance by `dt` seconds.
    The UI owns the clock and calls `update`.
    """

    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.organisms: list[Organism] = []
        self.time = 0.0  # simulation time in seconds
        self._next_id = 1
        for _ in range(config.organisms):
            self._spawn()

    def _spawn(self) -> None:
        c = self.config
        self.organisms.append(
            Organism(
                id=self._next_id,
                x=random.random() * c.width,
                y=random.random() * c.height,
                heading=random.random() * 2 * math.pi,
            )
        )
        self._next_id += 1

    def update(self, dt: float) -> None:
        """Advance the simulation by `dt` seconds."""
        self.time += dt
        c = self.config

        for o in self.organisms:
            # Wander: continuously drift the heading by a random amount.
            # This will be replaced by real behavior (seek food / flee
            # predator) once organisms have senses.
            o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt

            o.x += math.cos(o.heading) * c.speed * dt
            o.y += math.sin(o.heading) * c.speed * dt

            # Toroidal world: wrap around the edges instead of hitting walls.
            self._wrap(o)

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

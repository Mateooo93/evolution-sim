"""EvoLab — artificial ecosystem simulator."""

import math
import random
from dataclasses import dataclass

from .food import Food
from .genome import Genome, move_speed_px, body_radius_px, random_genome
from .types import Organism


@dataclass
class WorldConfig:
    width: int
    height: int
    organisms: int  # starting organism count
    wander_turn_rate: float  # how eagerly a creature changes direction (rad/s)

    # --- energy ---------------------------------------------------------
    max_energy: float = 100.0
    # drain/s = (base + range*metabolism) * (1 + speed_cost*speed + size_cost*size)
    #          * (1 - efficiency_saving*efficiency)
    base_metabolism: float = 0.30  # energy/s at minimal traits
    metabolism_range: float = 0.55  # extra burn from the metabolism trait
    speed_cost: float = 0.6  # upkeep multiplier weight for speed trait
    size_cost: float = 0.8  # upkeep multiplier weight for size trait
    efficiency_saving: float = 0.5  # fraction of upkeep efficiency can erase

    # --- life ------------------------------------------------------------
    base_lifespan: float = 120.0  # seconds at lifespan trait 0
    lifespan_range: float = 480.0  # extra seconds at lifespan trait 1

    # --- food -------------------------------------------------------------
    food_spawn_rate: float = 2.0  # food items per second
    max_food: int = 250  # food cap (the world is finite)
    food_energy: float = 30.0  # energy per food item

    # --- senses ------------------------------------------------------------
    vision_base: float = 30.0  # sensing range in px at vision trait 0
    vision_range: float = 120.0  # extra range at vision trait 1
    sense_interval: float = 0.25  # seconds between re-senses
    hungry_level: float = 0.70  # fraction of max energy below which food is sought
    steer_rate: float = 6.0  # max turn toward target (rad/s), agility drops with size

    # --- immigration -----------------------------------------------------
    # Safety net: a stream of fresh random immigrants keeps the lab
    # population from emptying out entirely. Tightly coupled to births
    # (reproduction milestone) — watch for its removal then.
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
        self.food: list[Food] = []
        self.time = 0.0  # simulation time in seconds
        self.deaths: dict[str, int] = {"starvation": 0, "age": 0}
        self._next_id = 1
        self._migration_acc = 0.0
        self._food_acc = 0.0
        self._food_ids: set[int] = set()
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

    # --- food -------------------------------------------------------------

    def _spawn_food(self) -> None:
        c = self.config
        f = Food(
            id=self._next_id,  # shares the id space with organisms — ids are unique
            x=random.random() * c.width,
            y=random.random() * c.height,
            energy=c.food_energy,
        )
        self._next_id += 1
        self.food.append(f)
        self._food_ids.add(f.id)

    def _eat_food(self, f: Food) -> None:
        self.food.remove(f)
        self._food_ids.discard(f.id)

    def _update_food(self, dt: float) -> None:
        c = self.config
        if len(self.food) >= c.max_food:
            self._food_acc = 0.0
            return
        self._food_acc += dt * c.food_spawn_rate
        while self._food_acc >= 1.0 and len(self.food) < c.max_food:
            self._food_acc -= 1.0
            self._spawn_food()

    # --- sensing -----------------------------------------------------------

    def _vision_range(self, o: Organism) -> float:
        c = self.config
        return c.vision_base + o.genome.vision * c.vision_range

    def _sense_food(self, o: Organism) -> None:
        """Point `o.target` at the nearest food within vision, or None.

        Toroidal: distances are computed across the wrapped world.
        """
        c = self.config
        range_px = self._vision_range(o)
        r2 = range_px * range_px
        half_w, half_h = c.width / 2, c.height / 2

        best = None
        best_d2 = r2
        for f in self.food:
            dx = f.x - o.x
            if dx > half_w:
                dx -= c.width
            elif dx < -half_w:
                dx += c.width
            if dx * dx > best_d2:
                continue  # early reject on x alone
            dy = f.y - o.y
            if dy > half_h:
                dy -= c.height
            elif dy < -half_h:
                dy += c.height
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best = f
        o.target = best

    # --- behaviour ------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the simulation by `dt` seconds."""
        self.time += dt
        c = self.config

        for o in list(self.organisms):
            o.age += dt

            # Decide what to do
            hungry = o.energy < c.hungry_level * c.max_energy

            # Re-scan for food when hungry and the target is missing or
            # stale, throttled to sense_interval so a population with no
            # food in sight cannot scan every tick.
            if hungry and self.time - o.last_sense >= c.sense_interval:
                if o.target is None or o.target.id not in self._food_ids:
                    self._sense_food(o)
                    o.last_sense = self.time

            if hungry and o.target is not None:
                self._steer_toward(o, dt)
            else:
                # Wander: continuously drift the heading by a random amount.
                # Predator behavior (flee) will replace this branch later.
                o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt

            o.x += math.cos(o.heading) * move_speed_px(o.genome) * dt
            o.y += math.sin(o.heading) * move_speed_px(o.genome) * dt

            # Toroidal world: wrap around the edges instead of hitting walls.
            self._wrap(o)

            o.energy = max(0.0, o.energy - self._drain(o.genome) * dt)
            if o.energy <= 0.0:
                self._kill(o, "starvation")
                continue
            if o.age >= self._max_age(o.genome):
                self._kill(o, "age")
                continue

            # Eat: touching the targeted food
            if o.target is not None and o.target.id in self._food_ids and hungry:
                dx = o.target.x - o.x
                if dx > c.width / 2:
                    dx -= c.width
                elif dx < -c.width / 2:
                    dx += c.width
                dy = o.target.y - o.y
                if dy > c.height / 2:
                    dy -= c.height
                elif dy < -c.height / 2:
                    dy += c.height
                reach = body_radius_px(o.genome.size) + 3
                if dx * dx + dy * dy <= reach * reach:
                    o.energy = min(c.max_energy, o.energy + o.target.energy)
                    self._eat_food(o.target)
                    o.target = None

        self._update_food(dt)
        self._migrate(dt)

    def _steer_toward(self, o: Organism, dt: float) -> None:
        """Turn the heading toward the target at a max rate (toroidal).

        Agility drops with size: big creatures are sluggish.
        """
        c = self.config
        t = o.target
        dx = t.x - o.x
        if dx > c.width / 2:
            dx -= c.width
        elif dx < -c.width / 2:
            dx += c.width
        dy = t.y - o.y
        if dy > c.height / 2:
            dy -= c.height
        elif dy < -c.height / 2:
            dy += c.height

        desired = math.atan2(dy, dx)
        diff = math.atan2(math.sin(desired - o.heading), math.cos(desired - o.heading))
        turn = c.steer_rate * (1.0 - 0.5 * o.genome.size)
        o.heading += max(-turn * dt, min(turn * dt, diff))

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

    def _migrate(self, dt: float) -> None:
        c = self.config
        if len(self.organisms) >= c.min_population:
            self._migration_acc = 0.0
            return
        self._migration_acc += dt * c.migration_rate
        while self._migration_acc >= 1.0 and len(self.organisms) < c.min_population:
            self._migration_acc -= 1.0
            self._spawn()

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

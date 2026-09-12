"""EvoLab — artificial ecosystem simulator."""

import math
import random
from dataclasses import dataclass

from .food import Food
from .genome import (
    Genome,
    move_speed_px,
    body_radius_px,
    random_genome,
    crossover,
    mutate,
)
from .spatial import SpatialGrid
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
    max_food: int = 300  # food cap (the world is finite)
    food_energy: float = 30.0  # energy per food item
    initial_food_fraction: float = 0.6  # food present at t=0 (world starts alive)

    # --- senses ------------------------------------------------------------
    vision_base: float = 30.0  # sensing range in px at vision trait 0
    vision_range: float = 120.0  # extra range at vision trait 1
    sense_interval: float = 0.25  # seconds between re-senses
    hungry_level: float = 0.80  # fraction of max energy below which food is sought
    steer_rate: float = 6.0  # max turn toward target (rad/s), agility drops with size

    # --- reproduction -----------------------------------------------------
    mate_radius: float = 30.0  # partners must be within this distance
    mate_energy_gate: float = 50.0  # energy required to mate
    mate_cost: float = 18.0  # energy each parent spends
    baby_energy: float = 30.0  # energy a newborn starts with
    readiness_base: float = 0.10  # readiness gained/s at fertility 0
    readiness_fertility: float = 0.45  # extra gained/s at fertility 1
    # Aggressive organisms breed slower — a direct reproductive edge for
    # prey that keeps the population majority herbivore even under raids.
    repro_aggression_penalty: float = 0.8
    max_population: int = 300  # no births above this (safety valve)
    mutation_rate: float = 0.05  # per-trait mutation probability (slider-driven)
    # --- immigration -----------------------------------------------------
    # Safety net: a stream of fresh random immigrants keeps the lab
    # population from emptying out entirely. Now that reproduction is
    # live it rarely fires, but it guards against total extinction.
    min_population: int = 40
    migration_rate: float = 1.0  # immigrants per second while below floor

    # --- predation -----------------------------------------------------
    # Predation is continuous, driven by the aggression trait on a
    # 0..1 spectrum. Every hungry organism hunts weaker neighbours with
    # probability = aggression, and forages plant food with probability
    # (1 - aggression). Aggression also adds an upkeep surcharge, so a
    # truly carnivorous lifestyle has to pay for itself. Because the
    # benefit scales smoothly with the trait, aggressive predators can
    # evolve from a clean herbivore lineage step by step in mutations.
    predation_drain: float = 2.5  # steep upkeep: hunting must pay for itself
    prey_energy_gain: float = 22.0  # energy a predator gains per catch
    capture_bonus: float = 6.0  # px added to reach beyond both radii
    hunt_interval: float = 0.15  # seconds between prey re-scans
    # Aggression must exceed a sensed organism's by at least this margin
    # for it to count as prey (and to trigger fleeing) — so similar
    # neighbours ignore each other instead of flinching constantly.
    hunt_margin: float = 0.1
    flee_strength: float = 2.6  # how hard a weak-minded organism turns away
    flee_speed_boost: float = 1.5  # sprint multiplier while fleeing
    flee_drain_cost: float = 1.2  # extra drain/s while sprinting
    # Predators must stock far more energy to breed, so predator numbers
    # lag prey availability (predator-prey cycling) instead of flooding.
    predator_mate_gate_mult: float = 2.0


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
        self.deaths: dict[str, int] = {"starvation": 0, "age": 0, "eaten": 0}
        self.births = 0  # lifetime count of births
        # (t, avg_speed, avg_size, population, avg_aggression) / sim second
        self.history: list[tuple[float, float, float, int, float]] = []
        self._history_acc = 0.0
        self.grid = SpatialGrid(config.width, config.height)
        self._next_id = 1
        self._migration_acc = 0.0
        self._food_acc = 0.0
        self._food_ids: set[int] = set()
        self.eaten = 0  # lifetime count of food items consumed
        # Seed the world with a fully prey population (aggression pinned to
        # zero) so predators are not present at t=0: they emerge later as
        # aggressive mutations spread. That is the arc you actually watch.
        for _ in range(config.organisms):
            self._spawn(initial_prey=True)
        # The world starts with food already on the plate, not empty.
        for _ in range(int(config.max_food * config.initial_food_fraction)):
            self._spawn_food()

    # --- population -----------------------------------------------------

    def _spawn(self, initial_prey: bool = False) -> None:
        c = self.config
        if initial_prey:
            # Pin aggression to zero so the founder stock is all prey.
            # Predators then arise only as aggressive mutations spread.
            genome = random_genome()
            genome.aggression = 0.0
        else:
            genome = random_genome()
        self.organisms.append(
            Organism(
                id=self._next_id,
                x=random.random() * c.width,
                y=random.random() * c.height,
                heading=random.random() * 2 * math.pi,
                genome=genome,
                energy=random.uniform(0.4, 1.0) * c.max_energy,
                age=0.0,
            )
        )
        self._next_id += 1

    def _kill(self, o: Organism, cause: str) -> None:
        """Flag an organism as dead; swept out at the end of the tick.

        Marking (rather than list.remove) keeps the per-organism update
        loop safe: a predator may eat a prey that is still ahead in the
        iteration, and the prey then skips its turn because it is dead.
        """
        if not o.dead:
            o.dead = True
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
        self.eaten += 1

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

    def _hunts(self, o: Organism, p: Organism) -> bool:
        """Whether `o` would treat `p` as prey: p must be meaningfully
        weaker (lower aggression) and alive."""
        return (
            not p.dead
            and p is not o
            and o.genome.aggression - p.genome.aggression >= self.config.hunt_margin
        )

    def _scan_prey(self, o: Organism) -> None:
        """Point `o.prey_target` at the nearest weaker neighbour in vision."""
        c = self.config
        range_px = self._vision_range(o)
        r2 = range_px * range_px
        half_w, half_h = c.width / 2, c.height / 2
        best = None
        best_d2 = r2
        for p in self.organisms:
            if not self._hunts(o, p):
                continue
            dx = p.x - o.x
            if dx > half_w:
                dx -= c.width
            elif dx < -half_w:
                dx += c.width
            if dx * dx > best_d2:
                continue
            dy = p.y - o.y
            if dy > half_h:
                dy -= c.height
            elif dy < -half_h:
                dy += c.height
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best = p
        o.prey_target = best

    def _scan_danger(self, o: Organism) -> None:
        """Point `o.danger` at the nearest meaningfully-stronger neighbour
        (a threat) in vision, or None."""
        c = self.config
        range_px = self._vision_range(o)
        r2 = range_px * range_px
        half_w, half_h = c.width / 2, c.height / 2
        best = None
        best_d2 = r2
        for p in self.organisms:
            if (
                p.dead
                or p is o
                or p.genome.aggression - o.genome.aggression < c.hunt_margin
            ):
                continue
            dx = p.x - o.x
            if dx > half_w:
                dx -= c.width
            elif dx < -half_w:
                dx += c.width
            if dx * dx > best_d2:
                continue
            dy = p.y - o.y
            if dy > half_h:
                dy -= c.height
            elif dy < -half_h:
                dy += c.height
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best = p
        o.danger = best

    def _flee(self, o: Organism, danger: Organism, dt: float) -> None:
        """Turn the heading away from `danger` (toroidal bearing).

        Prey with some aggression stand their ground a little: the
        turning response is scaled by (1 - aggression), so nearly-pure
        prey run hard while borderline predators barely flinch.
        """
        c = self.config
        dx = o.x - danger.x
        if dx > c.width / 2:
            dx -= c.width
        elif dx < -c.width / 2:
            dx += c.width
        dy = o.y - danger.y
        if dy > c.height / 2:
            dy -= c.height
        elif dy < -c.height / 2:
            dy += c.height
        desired = math.atan2(dy, dx)  # bearing toward the danger
        away = desired + math.pi
        diff = math.atan2(math.sin(away - o.heading), math.cos(away - o.heading))
        turn = c.flee_strength * (1.0 - 0.5 * o.genome.size) * (1.0 - 0.7 * o.genome.aggression)
        o.heading += max(-turn * dt, min(turn * dt, diff))

    def _turn(self, o: Organism, dt: float) -> None:
        """Decide one organism's movement for this tick (continuous roles).

        Highest priority is fleeing a real threat — an organism with
        meaningfully more aggression nearby. Otherwise, when hungry, the
        aggression trait draws a line between hunting (chase weaker
        neighbours) and foraging (chase plant food): a soft commit per
        hunger span, so a creature doesn't flap between roles every tick.
        A well-fed organism just wanders, which is what lets prey breed
        between raids.
        """
        c = self.config

        # Fleeing outranks everything.
        if o.danger is not None and not o.danger.dead:
            o.fleeing = True
            self._flee(o, o.danger, dt)
            return

        hungry = o.energy < c.hungry_level * c.max_energy
        if not hungry:
            o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt
            return

        # Choose a role once per hunger span, gated by the aggression trait.
        # `on_hunt` persists until the quarry dies or is caught. Do NOT
        # bump last_sense here — that throttle belongs to the food scan
        # alone, otherwise a would-be forager never re-senses food.
        if o.prey_target is None or o.prey_target.dead or self.time - o.last_hunt >= c.hunt_interval:
            o.on_hunt = random.random() < o.genome.aggression

        if o.on_hunt:
            if o.prey_target is None or o.prey_target.dead:
                self._scan_prey(o)
            if o.prey_target is not None and not o.prey_target.dead:
                # Reuse the steer; `_steer_toward` reads o.target, so point
                # it at the quarry for the turn then restore.
                saved = o.target
                o.target = o.prey_target  # type: ignore[assignment]
                self._steer_toward(o, dt)
                o.target = saved
            else:
                o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt
            return

        # Foraging for plant food.
        if self.time - o.last_sense >= c.sense_interval:
            if o.target is None or o.target.id not in self._food_ids:
                self._sense_food(o)
                o.last_sense = self.time
        if o.target is not None:
            self._steer_toward(o, dt)
        else:
            o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt

    def _try_catch(self, o: Organism) -> None:
        """Catch the hunted prey: kill it and gain energy.

        Catching is a hard speed gate: a predator only catches prey that
        it can actually outrun while the prey sprints away. A faster prey
        is uncatchable and gets away, so the arms race is real — prey
        evolve speed to escape, predators evolve speed to chase — and a
        lone carnivore cannot clear the whole plate, because the faster
        prey simply outlive it.
        """
        c = self.config
        prey = o.prey_target
        if prey is None or prey.dead:
            return
        dx = prey.x - o.x
        if dx > c.width / 2:
            dx -= c.width
        elif dx < -c.width / 2:
            dx += c.width
        dy = prey.y - o.y
        if dy > c.height / 2:
            dy -= c.height
        elif dy < -c.height / 2:
            dy += c.height
        reach = body_radius_px(o.genome.size) + body_radius_px(prey.genome.size) + c.capture_bonus
        if dx * dx + dy * dy > reach * reach:
            return

        pred_speed = move_speed_px(o.genome)
        prey_sprint = move_speed_px(prey.genome) * c.flee_speed_boost
        if pred_speed < prey_sprint:
            return  # outrun: the prey escapes
        o.energy = min(c.max_energy, o.energy + c.prey_energy_gain)
        self._kill(prey, "eaten")
        o.prey_target = None

    def _try_eat(self, o: Organism) -> None:
        """Plant food: gain the food's energy when touching it."""
        c = self.config
        f = o.target
        if f is None or f.id not in self._food_ids:
            return
        dx = f.x - o.x
        if dx > c.width / 2:
            dx -= c.width
        elif dx < -c.width / 2:
            dx += c.width
        dy = f.y - o.y
        if dy > c.height / 2:
            dy -= c.height
        elif dy < -c.height / 2:
            dy += c.height
        reach = body_radius_px(o.genome.size) + 3
        if dx * dx + dy * dy <= reach * reach:
            o.energy = min(c.max_energy, o.energy + f.energy)
            self._eat_food(f)
            o.target = None

    # --- behaviour ------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the simulation by `dt` seconds."""
        self.time += dt
        c = self.config

        for o in list(self.organisms):
            if o.dead:
                continue  # a predator already ate it earlier this tick

            o.age += dt
            repro = (c.readiness_base + c.readiness_fertility * o.genome.fertility)
            repro *= 1.0 - c.repro_aggression_penalty * o.genome.aggression
            o.readiness += repro * dt

            # Re-sense danger on the sense cadence, then pick behaviour.
            if o.danger is None or o.danger.dead:
                if self.time - o.last_sense >= c.sense_interval:
                    self._scan_danger(o)
            self._turn(o, dt)

            speed = move_speed_px(o.genome)
            if o.fleeing:
                speed *= c.flee_speed_boost
            o.x += math.cos(o.heading) * speed * dt
            o.y += math.sin(o.heading) * speed * dt

            # Toroidal world: wrap around the edges instead of hitting walls.
            self._wrap(o)

            drain = self._drain(o.genome)
            if o.fleeing:
                drain += c.flee_drain_cost
            o.energy = max(0.0, o.energy - drain * dt)
            o.fleeing = False  # reset for the next tick
            if o.energy <= 0.0:
                self._kill(o, "starvation")
                continue
            if o.age >= self._max_age(o.genome):
                self._kill(o, "age")
                continue

            if o.on_hunt and o.prey_target is not None:
                # Closing in: catch the quarry that comes within reach.
                self._try_catch(o)
            else:
                # Eat plant food: touching the targeted food.
                self._try_eat(o)

        # Sweep out everything that died this tick (see `_kill` docstring).
        self.organisms = [o for o in self.organisms if not o.dead]

        self._update_food(dt)
        self.grid.rebuild(self.organisms)
        self._mate()
        self._migrate(dt)

        # Sample the stats graph once per simulated second.
        self._history_acc += dt
        if self._history_acc >= 1.0:
            self._history_acc -= 1.0
            self.history.append(
                (
                    self.time,
                    self.trait_average("speed"),
                    self.trait_average("size"),
                    len(self.organisms),
                    self.trait_average("aggression"),
                )
            )
            if len(self.history) > 300:
                del self.history[0]

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

    # --- reproduction -----------------------------------------------------

    def _mate(self) -> None:
        """Local mating: a ready, energetic organism pairs with a nearby
        ready partner; the two pay the cost and produce one mutated
        crossover baby at their (toroidal) midpoint.
        """
        c = self.config
        for o in list(self.organisms):
            if len(self.organisms) >= c.max_population:
                break
            # Carnivorous organisms must stock far more energy to breed, so
            # predator numbers lag prey availability instead of flooding.
            carnivory = o.genome.aggression
            gate = c.mate_energy_gate * (1.0 + (c.predator_mate_gate_mult - 1.0) * carnivory)
            if o.readiness < 1.0 or o.energy < gate:
                continue
            partner = self._find_partner(o)
            if partner is None:
                continue

            o.energy -= c.mate_cost
            partner.energy -= c.mate_cost
            o.readiness = 0.0
            partner.readiness = 0.0

            # Toroidal midpoint, so a pair straddling an edge still
            # produces a baby between them.
            dx = partner.x - o.x
            if dx > c.width / 2:
                dx -= c.width
            elif dx < -c.width / 2:
                dx += c.width
            dy = partner.y - o.y
            if dy > c.height / 2:
                dy -= c.height
            elif dy < -c.height / 2:
                dy += c.height

            genome = mutate(crossover(o.genome, partner.genome), c.mutation_rate)
            baby = Organism(
                id=self._next_id,
                x=o.x + dx / 2,
                y=o.y + dy / 2,
                heading=random.random() * 2 * math.pi,
                genome=genome,
                energy=c.baby_energy,
                age=0.0,
                generation=max(o.generation, partner.generation) + 1,
            )
            self._next_id += 1
            self._wrap(baby)
            self.organisms.append(baby)
            self.births += 1

    def _find_partner(self, o: Organism) -> Organism | None:
        """First ready, energetic neighbor within the mating radius."""
        c = self.config
        for p in self.grid.within(o.x, o.y, c.mate_radius):
            if p is not o and p.readiness >= 1.0 and p.energy >= c.mate_energy_gate:
                return p
        return None

    # --- trait costs -----------------------------------------------------

    def _drain(self, g: Genome) -> float:
        """Energy per second: metabolism × movement/body upkeep − efficiency.

        Predators pay an aggression surcharge so hunting has to actually
        pay for itself — an aggression-heavy genome that never catches
        prey starves, which is the whole selection pressure.
        """
        c = self.config
        metabolism = c.base_metabolism + g.metabolism * c.metabolism_range
        upkeep = 1.0 + g.speed * c.speed_cost + g.size * c.size_cost
        saving = 1.0 - g.efficiency * c.efficiency_saving
        aggression = 1.0 + g.aggression * c.predation_drain
        return metabolism * upkeep * saving * aggression

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

    def organism_at(self, x: float, y: float, tolerance: float = 0.0) -> Organism | None:
        """The nearest organism whose body (radius + tolerance) contains the
        point, or None. Used to pick organisms by clicking on the plate."""
        best: Organism | None = None
        best_d = None
        for o in self.organisms:
            r = body_radius_px(o.genome.size) + tolerance
            dx = o.x - x
            dy = o.y - y
            d2 = dx * dx + dy * dy
            if d2 <= r * r and (best_d is None or d2 < best_d):
                best = o
                best_d = d2
        return best

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

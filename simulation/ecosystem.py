"""EvoLab — artificial ecosystem simulator."""

import math
import random
from collections import deque
from dataclasses import dataclass
from typing import NamedTuple

from .food import Food
from .genome import (
    PREDATOR_MIN,
    PREY_MAX,
    Genome,
    move_speed_px,
    body_radius_px,
    random_genome,
    crossover,
    mutate,
)
from .spatial import SpatialGrid
from .types import Event, Organism


class Sample(NamedTuple):
    """One per-second observation of the world, for the trends chart."""

    t: float
    speed: float  # mean speed trait
    size: float  # mean size trait
    population: int
    aggression: float  # mean aggression trait
    food: int
    energy: float  # mean energy, as a fraction of max
    predators: int  # organisms above the predator aggression threshold


@dataclass
class WorldConfig:
    width: int
    height: int
    organisms: int  # starting organism count
    wander_turn_rate: float  # how eagerly a creature changes direction (rad/s)

    # --- energy ---------------------------------------------------------
    max_energy: float = 100.0
    # drain/s = (base + range*metabolism) * (1 + speed_cost*speed + size_cost*size)
    #          * (1 - efficiency_saving*efficiency) * (1 + predation_drain*aggression)
    base_metabolism: float = 0.22  # energy/s at minimal traits
    metabolism_range: float = 0.40  # extra burn from the metabolism trait
    speed_cost: float = 0.9  # upkeep weight for the speed trait
    size_cost: float = 0.8  # upkeep multiplier weight for size trait
    efficiency_saving: float = 0.5  # fraction of upkeep efficiency can erase

    # --- life ------------------------------------------------------------
    base_lifespan: float = 120.0  # seconds at lifespan trait 0
    lifespan_range: float = 480.0  # extra seconds at lifespan trait 1

    # --- food -------------------------------------------------------------
    # The plate is a flow, not a stock: the spawn rate sets how much
    # energy the ecosystem receives per second, and the population settles
    # where consumption meets supply.
    #
    # Food arrives in *patches* rather than scattered uniformly. Uniform
    # food makes speed a runaway scramble trait — when every meal is a
    # lone dot, the fastest creature wins every race and the population
    # converges on maximum speed, which in turn makes prey uncatchable and
    # predation impossible. Patches change that: a forager that finds a
    # meadow eats many meals without travelling, so speed stops being the
    # only thing that matters, and prey that gather at a patch are exactly
    # where a hunter knows to look.
    food_spawn_rate: float = 9.0  # food items per second (supply, not patches)
    food_patch_size: int = 10  # items dropped per patch
    food_patch_radius: float = 55.0  # px, spread of one patch
    max_food: int = 320  # food cap (the world is finite)
    food_energy: float = 12.0  # energy per food item — small meals, many of them
    initial_food_fraction: float = 0.35  # food present at t=0 (world starts alive)


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
    max_population: int = 400  # no births above this (safety valve)
    mutation_rate: float = 0.05  # per-trait mutation probability (slider-driven)
    # --- immigration -----------------------------------------------------
    # Safety net: a stream of fresh random immigrants keeps the lab
    # population from emptying out entirely. Now that reproduction is
    # live it rarely fires, but it guards against total extinction.
    min_population: int = 28
    migration_rate: float = 0.15  # immigrants per second while below floor

    # --- predation -------------------------------------------------------
    # Predation is continuous, driven by the aggression trait on a
    # 0..1 spectrum. Every hungry organism hunts weaker neighbours with
    # probability = aggression, and forages plant food with probability
    # (1 - aggression). The cost sits on the *behaviour* rather than on
    # the gene: a chase burns extra energy, so hunting has to pay for
    # itself, but carrying an aggression gene is nearly free. That keeps
    # the climb smooth — a mutant that hunts a little pays a little —
    # instead of digging a fitness valley no intermediate can cross.
    predation_drain: float = 0.3  # small upkeep surcharge (a hunter's body)
    hunt_drain_cost: float = 1.2  # extra drain/s while actively chasing prey
    prey_energy_gain: float = 45.0  # energy a predator gains per catch
    # A hunter's gut is built for meat: the same plant is worth less to
    # it. This is what keeps a grazer majority — mid-aggression creatures
    # are mediocre at both trades, so selection pushes the population
    # toward the two ends instead of everyone drifting to "hunter".
    forage_penalty: float = 0.2  # plant energy lost at full aggression
    capture_bonus: float = 6.0  # px added to reach beyond both radii
    # A hungry creature commits to hunting or foraging for a *span* of a
    # few seconds, so roles read as behaviour instead of flickering every
    # tick — and a hunter that finds nothing catchable goes back to plants
    # instead of burning energy on a hopeless chase.
    role_span: float = 2.5  # seconds committed to one role per decision
    # Aggression must exceed a sensed organism's by at least this margin
    # for it to count as prey (and to trigger fleeing) — so similar
    # neighbours ignore each other instead of flinching constantly.
    hunt_margin: float = 0.1
    # How much faster a hunter must be than its quarry before the chase
    # is worth starting. Small, because chases here are endurance
    # chases: a hunted organism can only sprint while it still has the
    # energy for it, and a predator that is even slightly faster runs it
    # down once it tires. Speed decides who escapes *alert and fresh*.
    catch_margin: float = 1.05
    # Speed is not free to use, only to have: below this fraction of max
    # energy an organism cannot sprint at all, which is the window a
    # hunter's stamina hunt lives in.
    sprint_energy_floor: float = 0.25
    chase_timeout: float = 10.0  # seconds before a hunter abandons a chase
    # A threat only counts as a threat if it could actually run you down:
    # prey that out-run a predator simply don't flee it. Paired with the
    # same speed test on the hunter's side, the arms race becomes a real
    # one — speed is a refuge, not decoration.
    # A predator must also be *close* before panic is worth its price.
    danger_range_frac: float = 0.45  # flight zone, as a fraction of vision
    flee_strength: float = 2.6  # how hard a weak-minded organism turns away
    flee_speed_boost: float = 1.35  # sprint multiplier while fleeing
    flee_drain_cost: float = 0.8  # extra drain/s while sprinting
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
        self.migrants = 0  # lifetime count of immigrants
        # Per-second observations for the trends chart.
        self.history: list[Sample] = []
        self._history_acc = 0.0
        self.grid = SpatialGrid(config.width, config.height)
        # A second grid for food, so sensing scales with what is actually
        # nearby instead of scanning every plant on the plate.
        self.food_grid = SpatialGrid(config.width, config.height)
        self._next_id = 1
        self._migration_acc = 0.0
        self._food_acc = 0.0
        self._food_ids: set[int] = set()
        self.eaten = 0  # lifetime count of food items consumed
        # Deepest genealogical generation reached so far (cheap to keep
        # here — the HUD shows it every frame).
        self.max_generation = 1
        # What happened lately, for the view layers (plate pulses, event
        # log). Drained by the UI with `take_events`; bounded so a long
        # unattended run can't grow it.
        self.events: deque[Event] = deque(maxlen=256)
        # Seed the world with a fully prey population (aggression pinned to
        # zero) so predators are not present at t=0: they emerge later as
        # aggressive mutations spread. That is the arc you actually watch.
        for _ in range(config.organisms):
            self._spawn(founder=True)
        # The world starts with food already on the plate, not empty.
        while len(self.food) < config.max_food * config.initial_food_fraction:
            self._spawn_patch()
        self.food_grid.rebuild(self.food)

    # --- events -----------------------------------------------------------

    def _emit(self, kind: str, x: float, y: float, actor: int, other: int = 0) -> None:
        self.events.append(Event(self.time, kind, x, y, actor, other))

    def take_events(self) -> list[Event]:
        """Drain everything that happened since the last call."""
        if not self.events:
            return []
        out = list(self.events)
        self.events.clear()
        return out

    # --- population -----------------------------------------------------

    def _spawn(self, founder: bool = False) -> None:
        """Add one organism: the founding stock at t=0, or an immigrant.

        Both arrive as foragers — aggression is pinned to zero — so
        predators only ever arise by mutation, and a dying world is
        reseeded with prey instead of being handed hunters by fiat.
        """
        c = self.config
        genome = random_genome()
        genome.aggression = 0.0
        o = Organism(
            id=self._next_id,
            x=random.random() * c.width,
            y=random.random() * c.height,
            heading=random.random() * 2 * math.pi,
            genome=genome,
            energy=random.uniform(0.4, 1.0) * c.max_energy,
            age=0.0,
            born_at=self.time,
        )
        # An immigrant founds its own family line; the founding stock
        # likewise starts one line each.
        o.lineage = o.id
        self._next_id += 1
        self.organisms.append(o)
        if not founder:
            self.migrants += 1
            self._emit("arrived", o.x, o.y, o.id)

    def _kill(self, o: Organism, cause: str, by: int = 0) -> None:
        """Flag an organism as dead; swept out at the end of the tick.

        Marking (rather than list.remove) keeps the per-organism update
        loop safe: a predator may eat a prey that is still ahead in the
        iteration, and the prey then skips its turn because it is dead.
        """
        if not o.dead:
            o.dead = True
            self.deaths[cause] = self.deaths.get(cause, 0) + 1
            kind = {"starvation": "starved", "age": "aged"}.get(cause, cause)
            self._emit(kind, o.x, o.y, o.id, by)

    # --- food -------------------------------------------------------------

    def _spawn_food(self, x: float | None = None, y: float | None = None) -> None:
        c = self.config
        f = Food(
            id=self._next_id,  # shares the id space with organisms — ids are unique
            x=random.random() * c.width if x is None else x,
            y=random.random() * c.height if y is None else y,
            energy=c.food_energy,
        )
        self._next_id += 1
        self.food.append(f)
        self._food_ids.add(f.id)

    def _spawn_patch(self) -> None:
        """Drop one clump of food — a meadow, not a speck."""
        c = self.config
        cx = random.random() * c.width
        cy = random.random() * c.height
        r = c.food_patch_radius
        for _ in range(c.food_patch_size):
            if len(self.food) >= c.max_food:
                return
            # Uniform inside the disc: sqrt keeps it from bunching at the
            # centre, so a patch reads as a patch and not a single blob.
            dist = math.sqrt(random.random()) * r
            angle = random.random() * 2 * math.pi
            self._spawn_food(
                (cx + math.cos(angle) * dist) % c.width,
                (cy + math.sin(angle) * dist) % c.height,
            )

    def _eat_food(self, f: Food, o: Organism) -> None:
        self.food.remove(f)
        self._food_ids.discard(f.id)
        self.eaten += 1
        self._emit("ate", f.x, f.y, o.id)

    def _update_food(self, dt: float) -> None:
        c = self.config
        if len(self.food) >= c.max_food:
            self._food_acc = 0.0
            return
        self._food_acc += dt * c.food_spawn_rate / c.food_patch_size
        while self._food_acc >= 1.0 and len(self.food) < c.max_food:
            self._food_acc -= 1.0
            self._spawn_patch()

    # --- sensing -----------------------------------------------------------

    def _vision_range(self, o: Organism) -> float:
        c = self.config
        return c.vision_base + o.genome.vision * c.vision_range

    def _sense_food(self, o: Organism) -> None:
        """Point `o.target` at the nearest food within vision, or None.

        The food grid is rebuilt once per tick, so an item eaten earlier
        this frame can still be in a bucket; the `_food_ids` filter skips
        those so the scan can't lock onto a meal that is already gone.
        """
        o.target = self.food_grid.nearest(
            o.x, o.y, self._vision_range(o), accept=self._is_live_food
        )

    def _is_live_food(self, f: Food) -> bool:
        return f.id in self._food_ids

    def _hunts(self, o: Organism, p: Organism) -> bool:
        """Whether `o` would treat `p` as prey: p must be meaningfully
        weaker (lower aggression) and alive."""
        return (
            not p.dead
            and p is not o
            and o.genome.aggression - p.genome.aggression >= self.config.hunt_margin
        )

    def _scan_prey(self, o: Organism) -> None:
        """Point `o.prey_target` at the nearest weaker neighbour in vision
        that this hunter could actually run down.

        `_outruns` is deliberately a *cruising* speed test: a quarry that
        is faster than the hunter can never be caught, but one of similar
        speed can be run to exhaustion. Chases are endurance chases.
        """
        o.prey_target = self.grid.nearest(
            o.x,
            o.y,
            self._vision_range(o),
            accept=lambda p: self._hunts(o, p) and self._outruns(o, p),
        )

    def _scan_danger(self, o: Organism) -> None:
        """Point `o.danger` at the nearest real threat in the flight zone.

        A neighbour is only a threat if it is meaningfully more aggressive
        *and* fast enough to run this organism down — a slower neighbour
        can never land a catch, so fleeing it would burn sprint energy for
        nothing. Panic is expensive; the world selects against creatures
        that panic at nothing.
        """
        c = self.config
        zone = self._vision_range(o) * c.danger_range_frac
        o.danger = self.grid.nearest(
            o.x,
            o.y,
            zone,
            accept=lambda p: self._threatens(p, o) and self._outruns(p, o),
        )

    def _threatens(self, p: Organism, o: Organism) -> bool:
        return (
            not p.dead
            and p is not o
            and p.genome.aggression - o.genome.aggression >= self.config.hunt_margin
        )

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

        # Commit to a role for a span of seconds (not per tick), gated by
        # the aggression trait. The commitment is what makes "hunter" and
        # "forager" read as behaviour on the plate instead of flickering.
        if self.time >= o.role_until:
            o.on_hunt = random.random() < o.genome.aggression
            o.role_until = self.time + c.role_span

        if o.on_hunt:
            if o.prey_target is None or o.prey_target.dead:
                self._scan_prey(o)
                o.last_hunt = self.time
                o.chase_started = self.time
            elif self.time - o.last_hunt >= c.sense_interval:
                # Look around for something better; the clock only resets
                # when the quarry actually changes, so a hunter that keeps
                # missing the same prey eventually gives up on it.
                held = o.prey_target
                self._scan_prey(o)
                o.last_hunt = self.time
                if o.prey_target is not held:
                    o.chase_started = self.time
            if o.prey_target is not None:
                if self.time - o.chase_started >= c.chase_timeout:
                    # This chase is going nowhere: it is faster than us, or
                    # we cannot turn tight enough. Stop paying for it.
                    o.prey_target = None
                else:
                    # Reuse the steer; `_steer_toward` reads o.target, so
                    # point it at the quarry for the turn, then restore.
                    saved = o.target
                    o.target = o.prey_target  # type: ignore[assignment]
                    self._steer_toward(o, dt)
                    o.target = saved
                    o.hunting = True
                    return
            # No quarry (or the chase was dropped): forage for the rest of
            # this span instead of burning energy on empty pursuit.
            o.on_hunt = False
            o.role_until = self.time + c.role_span

        # Foraging for plant food.
        if self.time - o.last_sense >= c.sense_interval:
            if o.target is None or o.target.id not in self._food_ids:
                self._sense_food(o)
                o.last_sense = self.time
        if o.target is not None:
            self._steer_toward(o, dt)
        else:
            o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt

    def _can_sprint(self, o: Organism) -> bool:
        """Sprinting costs energy, so it needs some in the tank."""
        return o.energy > self.config.max_energy * self.config.sprint_energy_floor

    def _outruns(self, o: Organism, p: Organism) -> bool:
        """Whether `o` is fast enough to run `p` down (given a fresh `p`)."""
        return move_speed_px(o.genome) >= move_speed_px(p.genome) * self.config.catch_margin

    def _try_catch(self, o: Organism) -> None:
        """Catch the hunted prey: kill it and gain energy.

        The catch is a speed contest against the quarry's *current* best:
        a fresh prey that is already sprinting away is uncatchable for a
        hunter of similar speed — but the sprint burns energy, so a
        slower or exhausted prey gets run down. That is what makes this an
        arms race instead of a wall: prey evolve speed to escape the first
        seconds, predators evolve speed to keep the chase alive.
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

        prey_speed = move_speed_px(prey.genome)
        if prey.fleeing and self._can_sprint(prey):
            prey_speed *= c.flee_speed_boost
        if move_speed_px(o.genome) < prey_speed * c.catch_margin:
            return  # outrun: the prey gets away

        o.energy = min(c.max_energy, o.energy + c.prey_energy_gain)
        self._kill(prey, "eaten", by=o.id)
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
            gain = f.energy * (1.0 - c.forage_penalty * o.genome.aggression)
            o.energy = min(c.max_energy, o.energy + gain)
            self._eat_food(f, o)
            o.target = None

    # --- behaviour ------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the simulation by `dt` seconds."""
        self.time += dt
        c = self.config
        # Sense against the food as it stood at the start of the tick; the
        # grid is a snapshot, and food eaten below is filtered on lookup.
        self.food_grid.rebuild(self.food)

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
            if o.fleeing and self._can_sprint(o):
                speed *= c.flee_speed_boost
            o.x += math.cos(o.heading) * speed * dt
            o.y += math.sin(o.heading) * speed * dt

            # Toroidal world: wrap around the edges instead of hitting walls.
            self._wrap(o)

            drain = self._drain(o.genome)
            if o.fleeing:
                drain += c.flee_drain_cost
            if o.hunting:
                drain += c.hunt_drain_cost
            o.energy = max(0.0, o.energy - drain * dt)
            o.fleeing = False  # reset for the next tick
            o.hunting = False
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
            pop = self.organisms
            n = len(pop)
            predators = 0
            for o in pop:
                if o.genome.aggression >= PREDATOR_MIN:
                    predators += 1
            self.history.append(
                Sample(
                    t=self.time,
                    speed=self.trait_average("speed"),
                    size=self.trait_average("size"),
                    population=n,
                    aggression=self.trait_average("aggression"),
                    food=len(self.food),
                    energy=(sum(o.energy for o in pop) / n / c.max_energy) if n else 0.0,
                    predators=predators,
                )
            )
            if len(self.history) > 600:
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
                # The line comes from the first parent; both parent links
                # are kept so a single creature's own descendants can be
                # traced later.
                lineage=o.lineage,
                parent_a=o.id,
                parent_b=partner.id,
                born_at=self.time,
            )
            self._next_id += 1
            self._wrap(baby)
            self.organisms.append(baby)
            self.births += 1
            self._emit("birth", baby.x, baby.y, baby.id, o.id)
            if baby.generation > self.max_generation:
                self.max_generation = baby.generation

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

    def role_counts(self) -> tuple[int, int, int]:
        """(prey, mixed, predators) — a single pass over the population."""
        prey = mixed = pred = 0
        for o in self.organisms:
            a = o.genome.aggression
            if a >= PREDATOR_MIN:
                pred += 1
            elif a >= PREY_MAX:
                mixed += 1
            else:
                prey += 1
        return prey, mixed, pred

    def mean_energy(self) -> float:
        """Mean energy as a fraction of the maximum, or 0 if empty."""
        pop = self.organisms
        if not pop:
            return 0.0
        return sum(o.energy for o in pop) / len(pop) / self.config.max_energy

    def lineage_members(self, lineage: int) -> set[int]:
        """Every living organism descended from the founder of a line."""
        return {o.id for o in self.organisms if o.lineage == lineage}

    def descendants_of(self, oid: int) -> set[int]:
        """Every living organism descended from `oid` (any depth).

        Walks the parent links of the living population, so it works for
        an ancestor that has already died — the line outlives the body.
        """
        children: dict[int, list[int]] = {}
        for o in self.organisms:
            if o.parent_a is not None:
                children.setdefault(o.parent_a, []).append(o.id)
            if o.parent_b is not None:
                children.setdefault(o.parent_b, []).append(o.id)
        found: set[int] = set()
        stack = [oid]
        while stack:
            for cid in children.get(stack.pop(), ()):
                if cid not in found:
                    found.add(cid)
                    stack.append(cid)
        return found

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

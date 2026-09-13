# the whole world. no pygame in here at all, the UI drives this from outside.
# everything is a float, nothing is exact, thats kind of the point

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


# one row of the trends chart, taken once per simulated second
class Sample(NamedTuple):
    t: float
    speed: float
    size: float
    population: int
    aggression: float
    food: int
    energy: float  # as a fraction of max
    predators: int


# how hard the aggression dial yanks a newborn toward the target, per birth.
# 0.4 is strong, i tried 0.1 first and you basically couldnt see it move
PRESSURE_PULL = 0.4


@dataclass
class WorldConfig:
    width: int
    height: int
    organisms: int  # starting organism count
    wander_turn_rate: float  # how eagerly a creature changes direction (rad/s)

    # --- energy ---------------------------------------------------------
    max_energy: float = 100.0
    # drain per second = metabolism stuff * body upkeep * efficiency * aggression
    base_metabolism: float = 0.22
    metabolism_range: float = 0.40
    speed_cost: float = 0.9
    size_cost: float = 0.8
    efficiency_saving: float = 0.5

    # --- life -----------------------------------------------------------
    base_lifespan: float = 120.0  # seconds when the trait is 0
    lifespan_range: float = 480.0  # so max age is between 2 and 10 minutes

    # --- food -----------------------------------------------------------
    # food comes in little patches (meadows) instead of evenly sprinkled
    # dots. with even food, whoever was fastest won literally every race
    # and after 10 minutes the whole plate was at max speed, which meant
    # nobody could ever catch anybody. patches fixed it
    food_spawn_rate: float = 9.0  # items per second (the supply, not patches)
    food_supply_scale: float = 1.0  # the FOOD dial. famine < 1.0 < boom
    food_patch_size: int = 10  # items per meadow
    food_patch_radius: float = 55.0
    max_food: int = 320  # hard cap or the plate turns into a carpet
    food_energy: float = 12.0  # small meals, lots of them
    initial_food_fraction: float = 0.35  # some at t=0 so it doesnt start dead

    # --- senses ---------------------------------------------------------
    vision_base: float = 30.0
    vision_range: float = 120.0  # so 30..150px depending on the trait
    sense_interval: float = 0.25  # dont rescan every frame, too slow
    hungry_level: float = 0.80  # under 80% energy it goes looking
    steer_rate: float = 6.0  # rad/s. big creatures turn slower

    # --- reproduction ---------------------------------------------------
    mate_radius: float = 30.0
    mate_energy_gate: float = 50.0
    mate_cost: float = 18.0  # each parent pays this
    baby_energy: float = 30.0
    readiness_base: float = 0.10
    readiness_fertility: float = 0.45
    # hunters breed slower, otherwise they just end up with the whole plate
    repro_aggression_penalty: float = 0.8
    # tried 1.5 here once, plate went extinct in 4 minutes. keep it at 0.8
    max_population: int = 400  # safety valve
    mutation_rate: float = 0.05  # the MUTATION slider writes into this
    # --- immigration ----------------------------------------------------
    # if everything dies we trickle in random strangers so the sim is never
    # just an empty plate. barely ever fires now that breeding works
    min_population: int = 28
    migration_rate: float = 0.15

    # --- predation ------------------------------------------------------
    # aggression is a 0..1 thing: hungry + a dice roll under aggression =
    # go hunting, otherwise go eat plants. important bit: the cost is on
    # the CHASE, not on carrying the gene. the early version taxed the
    # trait and nobody could ever evolve into a hunter, the middle ground
    # was just too expensive
    predation_drain: float = 0.3
    hunt_drain_cost: float = 1.2  # per second while actually chasing
    prey_energy_gain: float = 45.0  # a catch is worth about 4 plants
    # the AGGRESSION dial. 0.0 = leave evolution alone. +1 drags newborns
    # toward hunter and seeds the immigrants mean, -1 pushes back to grazers.
    # its a bias not a cheat, selection still gets the last word
    aggression_pressure: float = 0.0
    # hunters are bad at plants (wrong kind of gut) which is roughly what
    # keeps a grazer majority around. without it everything drifts to hunter
    forage_penalty: float = 0.2
    capture_bonus: float = 6.0
    # stick with a decision for a couple of seconds. without this they flip
    # between hunting and eating every single frame and you cant see what
    # any of them is doing
    role_span: float = 2.5
    # Aggression must exceed a sensed organism's by at least this margin
    # for it to count as prey (and to trigger fleeing) — so similar
    # neighbours ignore each other instead of flinching constantly.
    hunt_margin: float = 0.1
    # how much faster than someone you have to be to bother chasing them.
    # small on purpose, chases here are endurance chases, you win by still
    # being there when they run out of puff
    catch_margin: float = 1.05
    # under 25% energy you cant sprint at all. thats the window a hunt
    # lives in, otherwise everything just outruns everything forever
    sprint_energy_floor: float = 0.25
    chase_timeout: float = 10.0  # give up after this long, its not happening
    # you only panic if it is close AND faster than you. if it cant catch
    # you then running away just burns energy for nothing
    danger_range_frac: float = 0.45  # flight zone = 45% of your vision
    flee_strength: float = 2.6
    flee_speed_boost: float = 1.35
    flee_drain_cost: float = 0.8
    # predators need way more energy stored before they breed, so their
    # numbers lag behind the prey instead of all turning up at once
    predator_mate_gate_mult: float = 2.0


class Ecosystem:
    # all the state lives on this thing. it has no idea it is being drawn,
    # it just gets told "advance by dt" over and over by main.py

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
        # second grid just for food. scanning all 300 plants for every
        # creature was a disaster once the population got going
        self.food_grid = SpatialGrid(config.width, config.height)
        self._next_id = 1
        self._migration_acc = 0.0
        self._food_acc = 0.0
        self._food_ids: set[int] = set()
        self.eaten = 0  # how many plants have been eaten, all time
        # best generation so far. cheap to track here and the HUD wants it
        # every frame, no point looping the population for it
        self.max_generation = 1
        # recent happenings for the drawing code (pulses, the log panel).
        # the UI empties this with take_events(). maxlen so a 3 hour run
        # left open on a laptop doesnt eat all the memory
        self.events: deque[Event] = deque(maxlen=256)
        # start with a pure prey population. predators are supposed to
        # turn up on their own later once aggressive mutations spread
        for _ in range(config.organisms):
            self._spawn(founder=True)
        # and put some food down so we dont open on an empty plate
        while len(self.food) < config.max_food * config.initial_food_fraction:
            self._spawn_patch()
        self.food_grid.rebuild(self.food)

    # --- events -----------------------------------------------------------

    def _emit(self, kind: str, x: float, y: float, actor: int, other: int = 0) -> None:
        self.events.append(Event(self.time, kind, x, y, actor, other))

    def take_events(self) -> list[Event]:
        # give me everything since last time and forget it
        if not self.events:
            return []
        out = list(self.events)
        self.events.clear()
        return out

    # --- population -----------------------------------------------------

    def _spawn(self, founder: bool = False) -> None:
        # one new creature: the starting 90 at t=0, or an immigrant later.
        # they come in at whatever aggression the dial is set to (0.0 by
        # default) so this is where you can see the AGGRESSION dial bite
        # when a crash gets reseeded
        c = self.config
        genome = random_genome()
        genome.aggression = max(0.0, c.aggression_pressure)
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
        # everyone starts their own family line. kids inherit it later
        o.lineage = o.id
        self._next_id += 1
        self.organisms.append(o)
        if not founder:
            self.migrants += 1
            self._emit("arrived", o.x, o.y, o.id)

    def _kill(self, o: Organism, cause: str, by: int = 0) -> None:
        # just flag it, the body gets swept at the end of the tick.
        # do NOT remove from the list in here: a predator can eat someone
        # who hasnt had their turn yet this frame and that crashes the loop
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
        # drop a clump of food somewhere. sqrt on the random keeps it from
        # all bunching up in the middle (found that trick online)
        c = self.config
        cx = random.random() * c.width
        cy = random.random() * c.height
        r = c.food_patch_radius
        for _ in range(c.food_patch_size):
            if len(self.food) >= c.max_food:
                return
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
        self._food_acc += dt * c.food_spawn_rate * c.food_supply_scale / c.food_patch_size
        while self._food_acc >= 1.0 and len(self.food) < c.max_food:
            self._food_acc -= 1.0
            self._spawn_patch()

    # --- sensing -----------------------------------------------------------

    def _vision_range(self, o: Organism) -> float:
        c = self.config
        return c.vision_base + o.genome.vision * c.vision_range

    def _sense_food(self, o: Organism) -> None:
        # look for the closest plant in vision. the grid is one tick behind
        # so something eaten earlier this frame can still be sitting in a
        # bucket, hence the _food_ids check or they chase ghosts
        o.target = self.food_grid.nearest(
            o.x, o.y, self._vision_range(o), accept=self._is_live_food
        )

    def _is_live_food(self, f: Food) -> bool:
        # tiny helper so nearest() can filter, still not sure this is
        # cheaper than checking after the fact but it works
        return f.id in self._food_ids

    def _hunts(self, o: Organism, p: Organism) -> bool:
        # is p lunch? needs to be alive and clearly less aggressive than me.
        # the 0.1 margin stops similar creatures from flinching at each other
        return (
            not p.dead
            and p is not o
            and o.genome.aggression - p.genome.aggression >= self.config.hunt_margin
        )

    def _scan_prey(self, o: Organism) -> None:
        # nearest neighbour i could actually run down. the speed test is on
        # cruising speed not sprint speed, because i can chase someone of
        # similar speed until they get tired
        o.prey_target = self.grid.nearest(
            o.x,
            o.y,
            self._vision_range(o),
            accept=lambda p: self._hunts(o, p) and self._outruns(o, p),
        )

    def _scan_danger(self, o: Organism) -> None:
        # is anything scary close by. it has to be more aggressive than me
        # AND fast enough to catch me, otherwise panicking is just burning
        # energy for nothing (that bug cost me a whole evening once)
        c = self.config
        zone = self._vision_range(o) * c.danger_range_frac
        o.danger = self.grid.nearest(
            o.x,
            o.y,
            zone,
            accept=lambda p: self._threatens(p, o) and self._outruns(p, o),
        )

    def _threatens(self, p: Organism, o: Organism) -> bool:
        # does p look dangerous to o
        return (
            not p.dead
            and p is not o
            and p.genome.aggression - o.genome.aggression >= self.config.hunt_margin
        )

    def _flee(self, o: Organism, danger: Organism, dt: float) -> None:
        # turn away from the scary thing. creatures with some aggression in
        # them barely flinch, pure prey bolt. everything here is measured
        # the short way round because the world wraps
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
        # what is this one doing this tick. order of priority:
        #   1. run away from something that can actually catch me
        #   2. if not hungry, wander about
        #   3. if hungry, hunt or graze depending on the aggression roll
        # well fed creatures just potter around, thats what gives prey
        # enough peace to breed between the raids
        c = self.config

        # running away beats everything else
        if o.danger is not None and not o.danger.dead:
            o.fleeing = True
            self._flee(o, o.danger, dt)
            return

        hungry = o.energy < c.hungry_level * c.max_energy
        if not hungry:
            o.heading += (random.random() - 0.5) * 2 * c.wander_turn_rate * dt
            return

        # roll for a role and KEEP it for a few seconds. if we rerolled
        # every tick you just see them twitch between the two
        if self.time >= o.role_until:
            o.on_hunt = random.random() < o.genome.aggression
            o.role_until = self.time + c.role_span

        if o.on_hunt:
            if o.prey_target is None or o.prey_target.dead:
                self._scan_prey(o)
                o.last_hunt = self.time
                o.chase_started = self.time
            elif self.time - o.last_hunt >= c.sense_interval:
                # have another look round for something better. the timer
                # only resets if we actually swap target, so chasing the
                # same hopeless one forever is not possible
                held = o.prey_target
                self._scan_prey(o)
                o.last_hunt = self.time
                if o.prey_target is not held:
                    o.chase_started = self.time
            if o.prey_target is not None:
                if self.time - o.chase_started >= c.chase_timeout:
                    # this one isnt happening: too fast, or too nimble.
                    # stop paying for it and go eat a plant instead
                    o.prey_target = None
                else:
                    # steer_toward reads o.target, so temporarily point the
                    # food target at the prey and put it back after. bit of
                    # a hack but it saves duplicating the steering maths
                    saved = o.target
                    o.target = o.prey_target  # type: ignore[assignment]
                    self._steer_toward(o, dt)
                    o.target = saved
                    o.hunting = True
                    return
            # nothing to chase. graze for the rest of this span instead of
            # jogging around burning energy on nothing
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
        # sprinting needs energy in the tank
        return o.energy > self.config.max_energy * self.config.sprint_energy_floor

    def _outruns(self, o: Organism, p: Organism) -> bool:
        # am i fast enough to run them down
        return move_speed_px(o.genome) >= move_speed_px(p.genome) * self.config.catch_margin

    def _try_catch(self, o: Organism) -> None:
        # if the prey is close enough AND not currently outrunning me, its
        # dinner. note this checks whether it is sprinting RIGHT NOW, which
        # is the whole endurance chase thing: a fresh one gets away, a
        # knackered one doesnt, so speed is worth evolving on both sides
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
        # plants. eating them is just touching them
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
        reach = body_radius_px(o.genome.size) + 3  # +3 so it isnt pixel perfect
        if dx * dx + dy * dy <= reach * reach:
            # aggressive guts are worse at plants, see forage_penalty
            gain = f.energy * (1.0 - c.forage_penalty * o.genome.aggression)
            o.energy = min(c.max_energy, o.energy + gain)
            self._eat_food(f, o)
            o.target = None

    # --- behaviour ------------------------------------------------------

    def update(self, dt: float) -> None:
        # advance the world by dt seconds. this is the whole simulation
        self.time += dt
        c = self.config
        # put the food into the grid once per tick, sensing uses it
        self.food_grid.rebuild(self.food)

        for o in list(self.organisms):
            if o.dead:
                continue  # someone ate it earlier in this very loop

            o.age += dt
            repro = (c.readiness_base + c.readiness_fertility * o.genome.fertility)
            repro *= 1.0 - c.repro_aggression_penalty * o.genome.aggression
            o.readiness += repro * dt

            # check for danger every so often then decide what to do
            if o.danger is None or o.danger.dead:
                if self.time - o.last_sense >= c.sense_interval:
                    self._scan_danger(o)
            self._turn(o, dt)

            # actual movement
            speed = move_speed_px(o.genome)
            if o.fleeing and self._can_sprint(o):
                speed *= c.flee_speed_boost
            o.x += math.cos(o.heading) * speed * dt
            o.y += math.sin(o.heading) * speed * dt

            # wrap round the edges, no walls in this world
            self._wrap(o)

            drain = self._drain(o.genome)
            if o.fleeing:
                drain += c.flee_drain_cost
            if o.hunting:
                drain += c.hunt_drain_cost
            o.energy = max(0.0, o.energy - drain * dt)
            o.fleeing = False  # reset both, they are per tick flags
            o.hunting = False
            if o.energy <= 0.0:
                self._kill(o, "starvation")
                continue
            if o.age >= self._max_age(o.genome):
                self._kill(o, "age")
                continue

            if o.on_hunt and o.prey_target is not None:
                self._try_catch(o)  # in reach? then its a kill
            else:
                self._try_eat(o)

        # clear out the dead (see _kill, we only flag them during the loop)
        self.organisms = [o for o in self.organisms if not o.dead]

        self._update_food(dt)
        self.grid.rebuild(self.organisms)
        self._mate()
        self._migrate(dt)

        # the chart gets one row per simulated second
        self._history_acc += dt
        if self._history_acc >= 1.0:
            self._history_acc -= 1.0
            pop = self.organisms
            n = len(pop)
            total_energy = 0.0  # not used any more, left it in for now
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
        # turn toward whatever o.target is, at a limited rate. big guys are
        # sluggish so size isnt a free upgrade
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
        # breeding. both parents have to be ready + have the energy, both
        # pay, and the baby pops out between them with a shuffled genome
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

            # midpoint, measured the short way so a couple either side of
            # the edge still has the baby between them
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
            self._bias_newborn(genome)
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

    def _bias_newborn(self, genome: Genome) -> None:
        # the AGGRESSION dial does its work here, on every new baby.
        # at +1 each one lands 40% of the way toward full hunter, at -1
        # 40% toward grazer, and it only touches the aggression trait.
        # deliberately NOT a clamp - if the plate cant feed hunters you
        # just get a starving experiment, which is more interesting
        pressure = self.config.aggression_pressure
        if not pressure:
            return
        target = 1.0 if pressure > 0 else 0.0
        genome.aggression += (target - genome.aggression) * abs(pressure) * PRESSURE_PULL

    def _find_partner(self, o: Organism) -> Organism | None:
        # first neighbour that is also ready and can afford it
        c = self.config
        for p in self.grid.within(o.x, o.y, c.mate_radius):
            if p is not o and p.readiness >= 1.0 and p.energy >= c.mate_energy_gate:
                return p
        return None

    # --- trait costs -----------------------------------------------------

    def _drain(self, g: Genome) -> float:
        # energy per second. this formula is the whole game really, every
        # trait shows up in here and that is what makes them tradeoffs
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
        # population mean of one trait. used by the chart + the inspector
        pop = self.organisms
        if not pop:
            return 0.0
        return sum(getattr(o.genome, trait) for o in pop) / len(pop)

    def role_counts(self) -> tuple[int, int, int]:
        # (prey, mixed, predators) for the little diet bar in the sidebar
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
        # average energy as a fraction of full
        pop = self.organisms
        if not pop:
            return 0.0
        return sum(o.energy for o in pop) / len(pop) / self.config.max_energy

    def lineage_members(self, lineage: int) -> set[int]:
        # everyone alive from the same founder. this is what gets ringed
        # on the plate when you click a creature
        return {o.id for o in self.organisms if o.lineage == lineage}

    def descendants_of(self, oid: int) -> set[int]:
        # walk parent links down from oid. works even if oid is long dead
        # because the kids still point at it (the line outlives the body!)
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
        # what did i just click on. tolerance makes small creatures easier
        # to hit (they are like 4px wide)
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
        # walk off the right edge, come back on the left
        c = self.config
        if o.x < 0:
            o.x += c.width
        elif o.x >= c.width:
            o.x -= c.width
        if o.y < 0:
            o.y += c.height
        elif o.y >= c.height:
            o.y -= c.height

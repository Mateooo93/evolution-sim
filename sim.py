# the world. there is no pygame in this file so it can run without a window.
# the ui in main.py calls world.update(dt) and draws whatever is in here

import math
import random

# the eight genes, all 0.0 to 1.0. genes[SPEED] reads better than genes[0]
SPEED, SIZE, VISION, METABOLISM, FERTILITY, LIFESPAN, AGGRESSION, EFFICIENCY = range(8)
GENE_NAMES = ["speed", "size", "vision", "meta", "fert", "life", "agg", "eff"]

MAX_ENERGY = 100.0
HUNGRY = 0.8          # under 80% energy it goes looking for food or prey
LOOK_EVERY = 0.25     # seconds between looking around. every frame is too slow
HUNT_MARGIN = 0.1     # how much more aggressive you must be to eat someone
CATCH_MARGIN = 1.05   # how much faster you must be to catch them
SPRINT_FLOOR = 0.25   # under 25% energy you cannot sprint, so you get caught
SPRINT = 1.35         # sprint speed multiplier
FLEE_DRAIN = 0.8      # extra energy per second while running away
HUNT_DRAIN = 1.2      # extra energy per second while chasing
FORAGE_PENALTY = 0.2  # hunters get less out of plants
PREY_ENERGY = 45.0    # a catch is worth about four plants
FOOD_ENERGY = 12.0

MAX_POPULATION = 400
MIN_POPULATION = 28   # below this the game adds a random creature now and then
MIGRATE_RATE = 0.15

MATE_RADIUS = 30
MATE_ENERGY = 50
MATE_COST = 18
BABY_ENERGY = 30

FOOD_RATE = 9.0       # items per second, the FOOD slider changes this
PATCH_SIZE = 10       # a patch is a clump of this many items
PATCH_RADIUS = 55
MAX_FOOD = 320


def clamp(v):
    return max(0.0, min(1.0, v))


# what the genes turn into. these are the only places genes are read as
# something other than a number

def speed_px(genes):
    return 10 + genes[SPEED] * 60


def radius_px(genes):
    return 2 + genes[SIZE] * 6


def vision_px(genes):
    return 30 + genes[VISION] * 120


def max_age(genes):
    return 120 + genes[LIFESPAN] * 480


def drain_per_second(genes):
    # energy cost per second. every gene shows up in here, that is what
    # makes them a tradeoff instead of just "bigger is better"
    metabolism = 0.22 + genes[METABOLISM] * 0.40
    body = 1 + genes[SPEED] * 0.9 + genes[SIZE] * 0.8
    saving = 1 - genes[EFFICIENCY] * 0.5
    hunting = 1 + genes[AGGRESSION] * 0.3
    return metabolism * body * saving * hunting


class Creature:
    def __init__(self, x, y, genes, generation=1):
        self.x = x
        self.y = y
        self.genes = genes
        self.generation = generation
        self.angle = random.random() * math.tau
        self.energy = random.uniform(40, 100)
        self.age = 0.0
        self.ready = 0.0        # creeps up to 1.0, then it can breed
        self.trail = []         # last few positions, for the tail
        self.dead = False
        self.target = None      # food it is walking to
        self.chase = None       # creature it is hunting
        self.danger = None      # creature it is running from
        self.hunting = False    # set for one frame while chasing
        self.sprinting = False  # set for one frame while running
        self.last_look = 0.0


class World:
    def __init__(self, width, height, start=90):
        self.width = width
        self.height = height
        self.time = 0.0
        self.mutation = 0.05    # the MUTATION slider writes here
        self.food_rate = FOOD_RATE * 1.0   # the FOOD slider writes here
        self.pressure = 0.0     # the AGGRESSION slider writes here, -1 to 1
        self.births = 0
        self.starved = 0
        self.killed = 0
        self.eaten = 0
        self.food = []
        self._food_acc = 0.0
        self._migrate_acc = 0.0
        self.creatures = [self.new_creature() for _ in range(start)]
        for _ in range(12):
            self.spawn_patch()

    # --- making creatures -------------------------------------------------

    def new_creature(self, x=None, y=None, genes=None, generation=1):
        if x is None:
            x = random.random() * self.width
        if y is None:
            y = random.random() * self.height
        if genes is None:
            genes = [random.random() for _ in range(8)]
            # new arrivals come in as aggressive as the dial is set
            genes[AGGRESSION] = max(0.0, self.pressure)
        return Creature(x, y, genes, generation)

    def mix(self, genes_a, genes_b):
        # a baby gets each gene from one parent or the other at random
        baby = [random.choice(pair) for pair in zip(genes_a, genes_b)]
        for i in range(8):
            if random.random() < self.mutation:
                baby[i] = clamp(baby[i] + random.gauss(0, 0.15))
        if self.pressure:
            # the aggression dial leans on every baby
            target = 1.0 if self.pressure > 0 else 0.0
            baby[AGGRESSION] += (target - baby[AGGRESSION]) * abs(self.pressure) * 0.4
        return baby

    # --- geometry ---------------------------------------------------------

    def gap(self, x1, y1, x2, y2):
        # distance between two points, the short way round the edges
        dx = abs(x1 - x2)
        dx = min(dx, self.width - dx)
        dy = abs(y1 - y2)
        dy = min(dy, self.height - dy)
        return math.hypot(dx, dy)

    def turn_toward(self, c, x, y, dt):
        # turn a little bit toward a point. bigger creatures turn slower
        dx = x - c.x
        if dx > self.width / 2:
            dx -= self.width
        elif dx < -self.width / 2:
            dx += self.width
        dy = y - c.y
        if dy > self.height / 2:
            dy -= self.height
        elif dy < -self.height / 2:
            dy += self.height
        want = math.atan2(dy, dx)
        diff = math.atan2(math.sin(want - c.angle), math.cos(want - c.angle))
        turn = 6.0 * (1 - 0.5 * c.genes[SIZE]) * dt
        c.angle += max(-turn, min(turn, diff))

    def turn_away(self, c, x, y, dt):
        # same thing but pointing the other way
        self.turn_toward(c, x, y, dt)
        c.angle += math.pi

    # --- looking around ---------------------------------------------------

    def nearest_food(self, c):
        reach = vision_px(c.genes)
        best = None
        best_d = reach
        for f in self.food:
            d = self.gap(c.x, c.y, f[0], f[1])
            if d < best_d:
                best_d = d
                best = f
        return best

    def nearest_prey(self, c):
        # a creature i could eat: less aggressive than me, and slow enough
        # that i can catch it. this is the whole arms race in one loop
        reach = vision_px(c.genes)
        my_speed = speed_px(c.genes)
        best = None
        best_d = reach
        for other in self.creatures:
            if other is c or other.dead:
                continue
            if c.genes[AGGRESSION] - other.genes[AGGRESSION] < HUNT_MARGIN:
                continue
            if my_speed < speed_px(other.genes) * CATCH_MARGIN:
                continue
            d = self.gap(c.x, c.y, other.x, other.y)
            if d < best_d:
                best_d = d
                best = other
        return best

    def nearest_threat(self, c):
        # something scary: more aggressive, close, and fast enough to catch me
        zone = vision_px(c.genes) * 0.45
        my_speed = speed_px(c.genes)
        best = None
        best_d = zone
        for other in self.creatures:
            if other is c or other.dead:
                continue
            if other.genes[AGGRESSION] - c.genes[AGGRESSION] < HUNT_MARGIN:
                continue
            if speed_px(other.genes) < my_speed * CATCH_MARGIN:
                continue
            d = self.gap(c.x, c.y, other.x, other.y)
            if d < best_d:
                best_d = d
                best = other
        return best

    # --- one creature, one frame ------------------------------------------

    def step(self, c, dt):
        c.age += dt
        c.hunting = False
        c.sprinting = False
        ready_rate = 0.10 + 0.45 * c.genes[FERTILITY]
        ready_rate *= 1 - 0.8 * c.genes[AGGRESSION]   # hunters breed slower
        c.ready = min(1.0, c.ready + ready_rate * dt)

        if self.time - c.last_look >= LOOK_EVERY:
            c.last_look = self.time
            c.danger = self.nearest_threat(c)
            if c.danger is None and c.energy < HUNGRY * MAX_ENERGY:
                # hunt or graze, whichever the aggression gene says
                if random.random() < c.genes[AGGRESSION]:
                    c.chase = self.nearest_prey(c)
                    c.target = None
                else:
                    c.chase = None
                    c.target = self.nearest_food(c)

        speed = speed_px(c.genes)
        if c.danger is not None:
            self.turn_away(c, c.danger.x, c.danger.y, dt)
            if c.energy > SPRINT_FLOOR * MAX_ENERGY:
                speed *= SPRINT
                c.sprinting = True
        elif c.chase is not None:
            self.turn_toward(c, c.chase.x, c.chase.y, dt)
            c.hunting = True
            self.try_to_catch(c)
        elif c.target is not None:
            self.turn_toward(c, c.target[0], c.target[1], dt)
            self.try_to_eat(c)
        else:
            # nothing to do, wander
            c.angle += (random.random() - 0.5) * 3 * dt

        c.x = (c.x + math.cos(c.angle) * speed * dt) % self.width
        c.y = (c.y + math.sin(c.angle) * speed * dt) % self.height

        c.trail.append((c.x, c.y))
        if len(c.trail) > 8:
            del c.trail[0]

        drain = drain_per_second(c.genes)
        if c.sprinting:
            drain += FLEE_DRAIN
        if c.hunting:
            drain += HUNT_DRAIN
        c.energy -= drain * dt

        if c.energy <= 0:
            c.dead = True
            self.starved += 1
        elif c.age > max_age(c.genes):
            c.dead = True
            self.starved += 1

    def try_to_eat(self, c):
        reach = radius_px(c.genes) + 3
        if self.gap(c.x, c.y, c.target[0], c.target[1]) < reach:
            # aggressive guts are worse at plants
            gain = FOOD_ENERGY * (1 - FORAGE_PENALTY * c.genes[AGGRESSION])
            c.energy = min(MAX_ENERGY, c.energy + gain)
            if c.target in self.food:
                self.food.remove(c.target)
            self.eaten += 1
            c.target = None

    def try_to_catch(self, c):
        prey = c.chase
        if prey.dead:
            c.chase = None
            return
        reach = radius_px(c.genes) + radius_px(prey.genes) + 6
        if self.gap(c.x, c.y, prey.x, prey.y) > reach:
            return
        # a sprinting prey is faster, but only while it still has energy
        prey_speed = speed_px(prey.genes)
        if prey.sprinting and prey.energy > SPRINT_FLOOR * MAX_ENERGY:
            prey_speed *= SPRINT
        if speed_px(c.genes) < prey_speed * CATCH_MARGIN:
            return      # it got away
        prey.dead = True
        self.killed += 1
        c.energy = min(MAX_ENERGY, c.energy + PREY_ENERGY)
        c.chase = None

    # --- the whole world, one frame ---------------------------------------

    def update(self, dt):
        self.time += dt
        for c in self.creatures:
            self.step(c, dt)
        self.breed()
        self.spawn_food(dt)
        self.immigration(dt)
        self.creatures = [c for c in self.creatures if not c.dead]

    def breed(self):
        # the simple version: check every pair. at a couple of hundred
        # creatures that is about 20k distance checks a frame, which is fine
        babies = []
        for i, a in enumerate(self.creatures):
            if len(self.creatures) + len(babies) >= MAX_POPULATION:
                break
            gate = MATE_ENERGY * (1 + a.genes[AGGRESSION])
            if a.ready < 1 or a.energy < gate:
                continue
            for j in range(i + 1, len(self.creatures)):
                b = self.creatures[j]
                if b.ready < 1 or b.energy < MATE_ENERGY:
                    continue
                if self.gap(a.x, a.y, b.x, b.y) > MATE_RADIUS:
                    continue
                a.energy -= MATE_COST
                b.energy -= MATE_COST
                a.ready = 0.0
                b.ready = 0.0
                # the baby appears between the parents, the short way round
                dx = b.x - a.x
                if dx > self.width / 2:
                    dx -= self.width
                elif dx < -self.width / 2:
                    dx += self.width
                dy = b.y - a.y
                if dy > self.height / 2:
                    dy -= self.height
                elif dy < -self.height / 2:
                    dy += self.height
                genes = self.mix(a.genes, b.genes)
                baby = self.new_creature((a.x + dx / 2) % self.width,
                                         (a.y + dy / 2) % self.height,
                                         genes,
                                         max(a.generation, b.generation) + 1)
                baby.energy = BABY_ENERGY
                babies.append(baby)
                self.births += 1
                break
        self.creatures += babies

    def spawn_patch(self):
        # food comes in clumps, not single dots. find a clump and you can
        # eat several meals without walking anywhere
        cx = random.random() * self.width
        cy = random.random() * self.height
        for _ in range(PATCH_SIZE):
            if len(self.food) >= MAX_FOOD:
                return
            angle = random.random() * math.tau
            dist = math.sqrt(random.random()) * PATCH_RADIUS
            self.food.append([(cx + math.cos(angle) * dist) % self.width,
                              (cy + math.sin(angle) * dist) % self.height])

    def spawn_food(self, dt):
        if len(self.food) >= MAX_FOOD:
            return
        self._food_acc += dt * self.food_rate / PATCH_SIZE
        while self._food_acc >= 1 and len(self.food) < MAX_FOOD:
            self._food_acc -= 1
            self.spawn_patch()

    def immigration(self, dt):
        # if everything dies off, drop in a random creature now and then so
        # the plate is never just empty
        if len(self.creatures) >= MIN_POPULATION:
            self._migrate_acc = 0.0
            return
        self._migrate_acc += dt * MIGRATE_RATE
        while self._migrate_acc >= 1 and len(self.creatures) < MIN_POPULATION:
            self._migrate_acc -= 1
            self.creatures.append(self.new_creature())

    # --- things the ui asks for -------------------------------------------

    def population(self):
        return len(self.creatures)

    def max_generation(self):
        return max((c.generation for c in self.creatures), default=0)

    def mean_aggression(self):
        if not self.creatures:
            return 0.0
        return sum(c.genes[AGGRESSION] for c in self.creatures) / len(self.creatures)

    def creature_at(self, x, y, slack=3):
        # which creature did i just click on
        best = None
        best_d = 999
        for c in self.creatures:
            d = self.gap(x, y, c.x, c.y)
            if d < radius_px(c.genes) + slack and d < best_d:
                best_d = d
                best = c
        return best


def snapshot(world):
    # a cheap copy of one frame, used by the replay
    return {
        "creatures": [(c.x, c.y, c.energy, c.genes[AGGRESSION], c.genes[SIZE])
                      for c in world.creatures],
        "food": [[f[0], f[1]] for f in world.food],
    }

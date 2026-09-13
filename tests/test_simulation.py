"""Tests for the simulation layer.

The world is pure Python with no pygame, so it can be stepped directly in
tests. These cover the contracts the rest of the project leans on: descent
bookkeeping, the predation speed gate, the food supply, and the fact that
a time-machine snapshot is independent of the world it came from.

    .venv/bin/python -m unittest discover -s tests -v
"""

import random
import unittest

from simulation import snapshot
from simulation.ecosystem import Ecosystem, WorldConfig
from simulation.food import Food
from simulation.genome import Genome, role_of
from simulation.types import Organism


def small_world(**over) -> Ecosystem:
    """A small, deterministic world: no organisms, no food, no immigration.

    Tests place exactly the creatures and meals they care about; anything
    the world seeds by itself would be noise.
    """
    cfg = dict(width=200, height=160, organisms=0, wander_turn_rate=1.6,
               min_population=0, max_population=60, initial_food_fraction=0.0,
               max_food=64)
    cfg.update(over)
    return Ecosystem(WorldConfig(**cfg))


def spawn(world: Ecosystem, *, x: float, y: float, speed: float, size: float = 0.5,
          aggression: float = 0.0, energy: float = 50.0, heading: float = 0.0,
          **traits) -> Organism:
    """Place one hand-made organism in a world (test fixture)."""
    values = dict(speed=speed, size=size, vision=0.5, metabolism=0.5,
                  fertility=0.5, lifespan=0.5, aggression=aggression,
                  efficiency=0.5)
    values.update(traits)
    o = Organism(id=1000 + len(world.organisms), x=x, y=y, heading=heading,
                 genome=Genome(**values), energy=energy, age=0.0)
    o.lineage = o.id
    world.organisms.append(o)
    return o


def run(world: Ecosystem, seconds: float) -> None:
    for _ in range(int(seconds * 60)):
        world.update(1 / 60)


class DescentTest(unittest.TestCase):
    """Parent links and the family line survive generations."""

    def setUp(self) -> None:
        random.seed(1234)

    def test_birth_records_both_parents_and_the_line(self) -> None:
        world = small_world()
        parent = spawn(world, x=100, y=80, speed=0.6, energy=100.0)
        mate = spawn(world, x=110, y=80, speed=0.6, energy=100.0)
        parent.readiness = mate.readiness = 1.0
        run(world, 0.1)

        babies = [o for o in world.organisms if o.parent_a is not None]
        self.assertTrue(babies, "a ready pair should have bred")
        baby = babies[0]
        self.assertEqual({baby.parent_a, baby.parent_b}, {parent.id, mate.id})
        self.assertEqual(baby.generation, 2)
        self.assertEqual(baby.lineage, parent.lineage)
        self.assertEqual(world.max_generation, 2)

    def test_lineage_members_and_descendants_agree_for_one_line(self) -> None:
        world = small_world()
        founder = spawn(world, x=100, y=80, speed=0.6, energy=100.0)
        mate = spawn(world, x=110, y=80, speed=0.6, energy=100.0)
        mate.lineage = founder.lineage
        for o in (founder, mate):
            o.readiness = 1.0
        run(world, 0.1)

        line = world.lineage_members(founder.lineage)
        self.assertIn(founder.id, line)
        self.assertTrue(line - {founder.id, mate.id}, "children join the line")
        self.assertTrue(world.descendants_of(founder.id) <= line)
        self.assertTrue(world.descendants_of(founder.id))

    def test_descendants_reach_through_dead_ancestors(self) -> None:
        world = small_world()
        grandparent = spawn(world, x=100, y=80, speed=0.6, energy=100.0)
        # A child of the grandparent, then a grandchild of that child.
        child = spawn(world, x=100, y=80, speed=0.6, energy=100.0)
        child.parent_a, child.generation, child.lineage = (
            grandparent.id, 2, grandparent.lineage)
        grandchild = spawn(world, x=100, y=80, speed=0.6, energy=100.0)
        grandchild.parent_a, grandchild.generation, grandchild.lineage = (
            child.id, 3, grandparent.lineage)

        self.assertIn(grandchild.id, world.descendants_of(grandparent.id))
        # The ancestor itself is gone, and the line still resolves.
        world.organisms.remove(grandparent)
        self.assertIn(grandchild.id, world.descendants_of(grandparent.id))

    def test_role_labels_split_the_aggression_spectrum(self) -> None:
        self.assertEqual(role_of(0.0), "prey")
        self.assertEqual(role_of(0.5), "mixed")
        self.assertEqual(role_of(0.9), "predator")

    def test_role_counts_match_the_population(self) -> None:
        world = small_world()
        spawn(world, x=20, y=20, speed=0.5, aggression=0.0)
        spawn(world, x=40, y=20, speed=0.5, aggression=0.5)
        spawn(world, x=60, y=20, speed=0.5, aggression=0.9)
        spawn(world, x=80, y=20, speed=0.5, aggression=1.0)
        self.assertEqual(world.role_counts(), (1, 1, 2))


class PredationTest(unittest.TestCase):
    """Catching is a speed contest, and only worth starting if you can win."""

    def setUp(self) -> None:
        random.seed(7)

    def test_a_faster_hunter_catches_an_adjacent_quarry(self) -> None:
        world = small_world()
        hunter = spawn(world, x=100, y=80, speed=1.0, aggression=1.0, energy=50.0)
        prey = spawn(world, x=104, y=80, speed=0.0, aggression=0.0, energy=50.0)
        world.grid.rebuild(world.organisms)
        run(world, 0.5)
        self.assertTrue(prey.dead, "the hunter should have made the catch")
        self.assertIn("eaten", world.deaths)
        self.assertGreater(hunter.energy, 50.0)

    def test_a_hunter_never_chases_what_it_cannot_outrun(self) -> None:
        world = small_world()
        slow = spawn(world, x=100, y=80, speed=0.0, aggression=1.0, energy=50.0)
        fast = spawn(world, x=104, y=80, speed=1.0, aggression=0.0, energy=50.0)
        world.grid.rebuild(world.organisms)
        run(world, 1.0)
        self.assertFalse(fast.dead, "a slower hunter cannot catch a faster prey")
        self.assertIsNone(slow.prey_target)

    def test_kill_event_names_both_parties_and_drains(self) -> None:
        world = small_world()
        hunter = spawn(world, x=100, y=80, speed=1.0, aggression=1.0, energy=50.0)
        prey = spawn(world, x=104, y=80, speed=0.0, aggression=0.0, energy=50.0)
        world.grid.rebuild(world.organisms)
        run(world, 0.5)
        events = world.take_events()
        kills = [e for e in events if e.kind == "eaten"]
        self.assertEqual(len(kills), 1)
        self.assertEqual(kills[0].actor, prey.id)
        self.assertEqual(kills[0].other, hunter.id)
        self.assertEqual(world.take_events(), [], "events drain")

    def test_a_tired_organism_cannot_sprint(self) -> None:
        world = small_world()
        fresh = spawn(world, x=50, y=50, speed=0.5, energy=100.0)
        tired = spawn(world, x=60, y=50, speed=0.5, energy=1.0)
        self.assertTrue(world._can_sprint(fresh))
        self.assertFalse(world._can_sprint(tired))

    def test_starvation_kills_and_is_recorded(self) -> None:
        world = small_world()
        doomed = spawn(world, x=50, y=50, speed=0.5, energy=0.05,
                       metabolism=1.0, efficiency=0.0)
        run(world, 1.0)
        self.assertTrue(doomed.dead)
        self.assertEqual(world.deaths["starvation"], 1)
        self.assertIn("starved", [e.kind for e in world.take_events()])


class FoodTest(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(11)

    def test_food_never_exceeds_the_cap(self) -> None:
        world = small_world(max_food=40, food_spawn_rate=200.0, organisms=4)
        run(world, 20.0)
        self.assertLessEqual(len(world.food), 40)
        self.assertGreater(len(world.food), 0)

    def test_food_arrives_in_patches(self) -> None:
        world = small_world(max_food=100)
        self.assertEqual(len(world.food), 0)
        world._spawn_patch()
        self.assertEqual(len(world.food), world.config.food_patch_size)
        radius = world.config.food_patch_radius
        cx = sum(f.x for f in world.food) / len(world.food)
        cy = sum(f.y for f in world.food) / len(world.food)
        for f in world.food:
            self.assertLessEqual(abs(f.x - cx), radius)
            self.assertLessEqual(abs(f.y - cy), radius)

    def test_eating_gains_energy_and_clears_the_meal(self) -> None:
        world = small_world()
        eater = spawn(world, x=100, y=80, speed=0.5, energy=20.0, aggression=0.0)
        meal = Food(id=9999, x=100, y=80, energy=world.config.food_energy)
        world.food.append(meal)
        world._food_ids.add(meal.id)
        eater.target = meal
        world._try_eat(eater)
        self.assertNotIn(meal, world.food)
        self.assertGreater(eater.energy, 20.0)
        self.assertEqual(world.eaten, 1)

    def test_sensing_ignores_food_eaten_earlier_in_the_tick(self) -> None:
        """The food grid is rebuilt per tick, so a stale entry must not
        become a target — this guards the `_food_ids` filter."""
        world = small_world()
        eater = spawn(world, x=100, y=80, speed=0.5, energy=20.0)
        meal = Food(id=9999, x=100, y=80, energy=12.0)
        world.food.append(meal)
        world.food_grid.rebuild(world.food)
        world._eat_food(meal, eater)  # someone else got it first
        world._sense_food(eater)
        self.assertIsNone(eater.target)


class SensingPlacementTest(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(3)

    def test_nearest_food_wins_inside_vision(self) -> None:
        world = small_world()
        eater = spawn(world, x=100, y=80, speed=0.5, energy=20.0, vision=1.0)
        near = Food(id=1, x=110, y=80, energy=12.0)
        far = Food(id=2, x=140, y=80, energy=12.0)
        world.food.extend([near, far])
        world._food_ids.update({1, 2})
        world.food_grid.rebuild(world.food)
        world._sense_food(eater)
        self.assertIs(eater.target, near)

    def test_food_outside_vision_is_not_sensed(self) -> None:
        world = small_world()
        eater = spawn(world, x=100, y=80, speed=0.5, energy=20.0, vision=0.0)
        meal = Food(id=1, x=100 + world._vision_range(eater) + 20, y=80, energy=12.0)
        world.food.append(meal)
        world._food_ids.add(1)
        world.food_grid.rebuild(world.food)
        world._sense_food(eater)
        self.assertIsNone(eater.target)

    def test_threat_must_be_faster_to_be_worth_fleeing(self) -> None:
        world = small_world()
        prey = spawn(world, x=100, y=80, speed=0.8, aggression=0.0)
        slow_threat = spawn(world, x=110, y=80, speed=0.1, aggression=0.5)
        world.grid.rebuild(world.organisms)
        world._scan_danger(prey)
        self.assertIsNone(prey.danger, "a slower neighbour can never catch us")


        slow_threat.genome.speed = 1.0
        world.grid.rebuild(world.organisms)
        world._scan_danger(prey)
        self.assertIs(prey.danger, slow_threat)


class ToroidalWorldTest(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(5)

    def test_organisms_wrap_at_the_edges(self) -> None:
        world = small_world()
        runner = spawn(world, x=199.0, y=80, speed=1.0, heading=0.0, energy=100.0)
        run(world, 1.0)
        self.assertLess(runner.x, 100.0, "walked off the right edge and wrapped")
        self.assertGreaterEqual(runner.x, 0.0)

    def test_picking_uses_the_body_radius_and_tolerance(self) -> None:
        world = small_world()
        o = spawn(world, x=50, y=50, speed=0.5, size=0.0)  # 2px body
        self.assertIs(world.organism_at(51, 51, tolerance=3), o)
        self.assertIsNone(world.organism_at(70, 70, tolerance=3))


class SnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(17)

    def test_snapshot_is_a_copy_that_does_not_follow_the_world(self) -> None:
        world = small_world(organisms=6)
        run(world, 2.0)
        frame = snapshot.capture(world)
        self.assertEqual(len(frame["organisms"]), len(world.organisms))
        self.assertEqual(frame["time"], world.time)

        before = [(o.x, o.y) for o in frame["organisms"]]
        run(world, 2.0)
        after = [(o.x, o.y) for o in frame["organisms"]]
        self.assertEqual(before, after, "the stored frame is frozen in time")
        self.assertNotEqual(frame["time"], world.time)

    def test_snapshot_drops_live_only_pointers(self) -> None:
        world = small_world(organisms=4)
        world._sense_food(world.organisms[0])
        frame = snapshot.capture(world)
        for o in frame["organisms"]:
            self.assertIsNone(o.target)
            self.assertIsNone(o.prey_target)
            self.assertIsNone(o.danger)

    def test_history_is_sampled_once_per_simulated_second(self) -> None:
        world = small_world(organisms=5, food_spawn_rate=0.0)
        run(world, 3.0)
        self.assertEqual(len(world.history), 3)
        self.assertAlmostEqual(world.history[-1].t, 3.0, places=6)
        # Nothing dies inside three seconds on a full tank, so the sample
        # must agree with the population standing right now.
        self.assertEqual(world.history[-1].population, len(world.organisms))
        self.assertEqual(world.history[-1].food, len(world.food))


if __name__ == "__main__":
    unittest.main()

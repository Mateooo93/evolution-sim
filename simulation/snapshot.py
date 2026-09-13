# time machine snapshots. we copy the world every 0.25s so replay can show
# an old frame without touching the real one.
# copy.copy is enough because all we need is position/genome/energy, the
# "who am i chasing" pointers are useless once the frame is old

import copy

from .types import Organism


def capture(world) -> dict:
    return {
        "time": world.time,
        "organisms": [_copy_organism(o) for o in world.organisms],
        "food": [copy.copy(f) for f in world.food],
    }


def _copy_organism(o: Organism) -> Organism:
    c = copy.copy(o)
    # these point at live creatures, they go stale the moment we store them
    c.target = None
    c.prey_target = None
    c.danger = None
    return c

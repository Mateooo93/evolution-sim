"""Time-machine snapshots: capture and restore (for display) the world
state so the game can replay the last minute or two.

A snapshot is a cheap, render-only copy of the ecosystems organisms and
food. Organisms are `copy.copy`ed and their transient chase pointers
(target/prey_target/danger) are cleared, since those reference live
objects that won't exist in a stored snapshot. Nothing here mutates the
live ecosystem — it only captures copies.
"""

import copy

from .types import Organism


def capture(world) -> dict:
    """A dict holding copies of the world's organisms and food plus time."""
    return {
        "time": world.time,
        "organisms": [_copy_organism(o) for o in world.organisms],
        "food": [copy.copy(f) for f in world.food],
    }


def _copy_organism(o: Organism) -> Organism:
    c = copy.copy(o)
    # Chase pointers go stale in a stored frame; render only needs the
    # position / genome / energy, so drop them.
    c.target = None
    c.prey_target = None
    c.danger = None
    return c
# drawing a creature as a little glowing dot.
# this lives on its own because the plate AND the inspector both need to
# draw the exact same looking orb

import pygame

from ui import theme

RADIUS_STEPS = list(range(2, 9))
ENERGY_LEVELS = 8   # brightness buckets. 8 looked smooth enough
AGGRESSION_BUCKETS = 8
GLOW = 2  # px of halo round the body

# what a creature looks like when its basically out of energy
_STARVED_PREY = (30, 90, 62)
_STARVED_PRED = (94, 38, 38)


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    # blend two colours. t=0 gives a, t=1 gives b
    return tuple(round(av + (bv - av) * t) for av, bv in zip(a, b))


def _orb_color(species: str, level: int) -> tuple[int, int, int]:
    # dim for a starving one, full colour for a full one
    t = level / (ENERGY_LEVELS - 1) if ENERGY_LEVELS > 1 else 1.0
    if species == "pred":
        return lerp(_STARVED_PRED, theme.PREDATOR, t)
    return lerp(_STARVED_PREY, theme.ACCENT, t)


def orb_color(aggression: float, level: int) -> tuple[int, int, int]:
    # green -> amber -> red depending on how murdery it is.
    # amber in the middle reads better than a straight green-red blend
    t = min(1.0, max(0.0, aggression))
    green = _orb_color("prey", level)
    red = _orb_color("pred", level)
    warm = lerp(green, red, 0.45)
    if t < 0.5:
        return lerp(green, warm, t * 2.0)
    return lerp(warm, red, (t - 0.5) * 2.0)


def energy_level(energy: float, max_energy: float) -> int:
    return min(
        ENERGY_LEVELS - 1,
        max(0, int(energy / max_energy * ENERGY_LEVELS)),
    )


def aggression_bucket(aggression: float) -> int:
    return min(AGGRESSION_BUCKETS - 1, max(0, int(aggression * AGGRESSION_BUCKETS)))


def make_orb(color: tuple[int, int, int], radius: int, glow: int = GLOW) -> pygame.Surface:
    # paint one dot: body, then a bright core inside, then a soft ring
    # outside it so it doesnt look like a hard circle
    side = (radius + glow) * 2 + 2
    surf = pygame.Surface((side, side), pygame.SRCALPHA)
    c = side // 2
    for rr in range(radius + glow, radius, -1):
        a = int(255 * (radius + glow - rr + 1) / (glow + 1))
        pygame.draw.circle(surf, (*color, a), (c, c), rr)
    pygame.draw.circle(surf, (*color, 255), (c, c), radius)
    core = lerp(color, (255, 255, 255), 0.35)
    pygame.draw.circle(surf, (*core, 220), (c, c), max(1, int(radius * 0.7)))
    inner = lerp(color, (255, 255, 255), 0.65)
    pygame.draw.circle(surf, (*inner, 160), (c, c), max(1, int(radius * 0.4)))
    return surf

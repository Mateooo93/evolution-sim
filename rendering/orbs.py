"""Organism paint: the colour and orb sprites shared by the plate and the UI.

Kept separate from the renderer because the inspector draws the selected
creature as the same orb the plate uses — one definition of "what a
creature looks like", so a green dot in the panel is the same green as
the dot you clicked.
"""

import pygame

from ui import theme

RADIUS_STEPS = list(range(2, 9))  # rounded body radii (2..8 px)
ENERGY_LEVELS = 8  # brightness buckets for the atlas
AGGRESSION_BUCKETS = 8  # colour buckets for the aggression spectrum
GLOW = 2  # px of soft halo around each orb

# Colours at zero energy (dim) for each species.
_STARVED_PREY = (30, 90, 62)
_STARVED_PRED = (94, 38, 38)


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(av + (bv - av) * t) for av, bv in zip(a, b))


def _orb_color(species: str, level: int) -> tuple[int, int, int]:
    """Body colour for an atlas cell: brightness rises with the energy level."""
    t = level / (ENERGY_LEVELS - 1) if ENERGY_LEVELS > 1 else 1.0
    if species == "pred":
        return lerp(_STARVED_PRED, theme.PREDATOR, t)
    return lerp(_STARVED_PREY, theme.ACCENT, t)


def orb_color(aggression: float, level: int) -> tuple[int, int, int]:
    """Body colour across the aggression spectrum: herbivore green at low
    aggression, shifting through amber to carnivore red at high aggression.
    The energy level still controls brightness (dim = starving).
    """
    t = min(1.0, max(0.0, aggression))
    green = _orb_color("prey", level)
    red = _orb_color("pred", level)
    warm = lerp(green, red, 0.45)  # amber midpoint
    if t < 0.5:
        return lerp(green, warm, t * 2.0)
    return lerp(warm, red, (t - 0.5) * 2.0)


def energy_level(energy: float, max_energy: float) -> int:
    """Quantise an energy value into an atlas brightness bucket."""
    return min(
        ENERGY_LEVELS - 1,
        max(0, int(energy / max_energy * ENERGY_LEVELS)),
    )


def aggression_bucket(aggression: float) -> int:
    return min(AGGRESSION_BUCKETS - 1, max(0, int(aggression * AGGRESSION_BUCKETS)))


def make_orb(color: tuple[int, int, int], radius: int, glow: int = GLOW) -> pygame.Surface:
    """A soft-edged radial orb: full-colour body fading into the halo."""
    side = (radius + glow) * 2 + 2
    surf = pygame.Surface((side, side), pygame.SRCALPHA)
    c = side // 2
    # Halo: a thin fading ring outside the body.
    for rr in range(radius + glow, radius, -1):
        a = int(255 * (radius + glow - rr + 1) / (glow + 1))
        pygame.draw.circle(surf, (*color, a), (c, c), rr)
    # Body in full colour.
    pygame.draw.circle(surf, (*color, 255), (c, c), radius)
    # Brighter inner core for depth.
    core = lerp(color, (255, 255, 255), 0.35)
    pygame.draw.circle(surf, (*core, 220), (c, c), max(1, int(radius * 0.7)))
    inner = lerp(color, (255, 255, 255), 0.65)
    pygame.draw.circle(surf, (*inner, 160), (c, c), max(1, int(radius * 0.4)))
    return surf

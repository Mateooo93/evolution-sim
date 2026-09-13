# the selected panel. shows whatever you clicked on.
# the useful bit is the tick on each trait bar - it marks the population
# average, so you can see if this one is fast for its time or not

from typing import NamedTuple

import pygame

from simulation.genome import TRAIT_NAMES, body_radius_px, role_of
from simulation.types import Organism
from rendering.orbs import aggression_bucket, energy_level, make_orb, orb_color
from ui import theme

# short names for the traits, they have to fit next to a bar
TRAIT_LABELS = {
    "speed": "spd",
    "size": "size",
    "vision": "vis",
    "metabolism": "meta",
    "fertility": "fert",
    "lifespan": "life",
    "aggression": "agg",
    "efficiency": "eff",
}

CHIP = 32   # the portrait box
BAR_W = 52
BAR_H = 5


class Descent(NamedTuple):
    # family info for the selected creature
    line: int          # how many of its line are alive
    descendants: int   # how many came from this one specifically
    population: int    # for the percentage


class Inspector:
    def __init__(self, fonts) -> None:
        self.fonts = fonts
        self._chip = None
        self._chip_key = None

    def draw(self, surface: pygame.Surface, sidebar: pygame.Rect, top: int,
             bottom: int, o: Organism | None, config, averages: dict[str, float],
             descent: Descent | None) -> None:
        f = self.fonts
        pad = theme.PANEL_PAD
        x = sidebar.left + pad
        width = sidebar.width - 2 * pad
        y = top + pad

        surface.blit(f.head.render("selected", True, theme.TEXT), (x, y))
        y += f.head.get_height() + 6

        if o is None:
            surface.blit(f.small.render("click a creature", True, theme.TEXT_DIM), (x, y))
            surface.blit(f.small.render("to see its genome", True, theme.TEXT_FAINT),
                         (x, y + f.small.get_height() + 2))
            return

        y = self._identity(surface, x, y, o, config)
        y = self._meters(surface, x, width, y, o, config)
        self._traits(surface, x, width, y + 4, o, averages)
        self._descent(surface, x, width, bottom, o, descent)

    def _identity(self, surface, x, y, o: Organism, config) -> int:
        # little square with the creature drawn in it, exactly like the plate
        # draws it, so the thing in the panel is the thing you clicked
        chip = pygame.Rect(x, y, CHIP, CHIP)
        pygame.draw.rect(surface, theme.BG, chip)
        pygame.draw.rect(surface, theme.PANEL_BORDER, chip, width=1)
        orb = self._portrait(o, config)
        surface.blit(orb, orb.get_rect(center=chip.center))

        f = self.fonts
        tx = chip.right + 8
        surface.blit(f.body.render(f"#{o.id}  gen {o.generation}", True, theme.TEXT),
                     (tx, y + 1))
        role = role_of(o.genome.aggression)
        color = {"predator": theme.PREDATOR, "mixed": theme.FOOD,
                 "prey": theme.ACCENT}[role]
        surface.blit(f.small.render(f"{role}, line #{o.lineage}", True, color),
                     (tx, y + f.body.get_height() + 2))
        return y + CHIP + 8

    def _portrait(self, o: Organism, config) -> pygame.Surface:
        radius = max(3, round(body_radius_px(o.genome.size)))
        level = energy_level(o.energy, config.max_energy)
        agg = aggression_bucket(o.genome.aggression)
        key = (agg, radius, level)
        if key != self._chip_key:
            self._chip = make_orb(orb_color(agg / 7.0, level), radius, glow=3)
            self._chip_key = key
        return self._chip

    def _meters(self, surface, x, width, y, o: Organism, config) -> int:
        row = self.fonts.small.get_height() + 5
        life = config.base_lifespan + o.genome.lifespan * config.lifespan_range
        age_frac = o.age / life if life > 0 else 0.0
        self.meter_row(surface, x, y, width, "energy", o.energy / config.max_energy,
                       f"{o.energy:.0f}", theme.ACCENT)
        self.meter_row(surface, x, y + row, width, "age", age_frac,
                       f"{o.age:.0f}s", theme.ACCENT if age_frac < 0.75 else theme.FOOD)
        self.meter_row(surface, x, y + 2 * row, width, "ready", o.readiness,
                       "yes" if o.readiness >= 1.0 else "no",
                       theme.PREDATOR if o.readiness >= 1.0 else theme.TEXT_DIM)
        return y + 3 * row

    def meter_row(self, surface, x, y, width, label, frac, text, color) -> None:
        f = self.fonts
        surface.blit(f.small.render(label, True, theme.TEXT_DIM), (x, y))
        bar = pygame.Rect(x + 48, y + 3, width - 48 - 46, 7)
        pygame.draw.rect(surface, theme.METER_BG, bar)
        frac = max(0.0, min(1.0, frac))
        if frac > 0:
            pygame.draw.rect(surface, color,
                             (bar.left, bar.top, max(2, round(bar.width * frac)), bar.height))
        surface.blit(f.small.render(text, True, theme.TEXT), (bar.right + 6, y))

    def _traits(self, surface, x, width, y, o: Organism, averages: dict[str, float]) -> None:
        # 8 traits, two columns. averages[] is the population mean
        f = self.fonts
        row = f.tiny.get_height() + 6
        col = width // 2
        for i, name in enumerate(TRAIT_NAMES):
            cx = x + (i // 4) * col
            cy = y + (i % 4) * row
            self._trait(surface, cx, cy, name, getattr(o.genome, name),
                        averages.get(name, 0.0))

    def _trait(self, surface, x, y, name, value, average) -> None:
        f = self.fonts
        surface.blit(f.tiny.render(TRAIT_LABELS[name], True, theme.TEXT_FAINT), (x, y))
        bar = pygame.Rect(x + 28, y + 2, BAR_W, BAR_H)
        pygame.draw.rect(surface, theme.METER_BG, bar)
        if value > 0:
            pygame.draw.rect(surface, theme.ACCENT,
                             (bar.left, bar.top, max(1, round(BAR_W * min(1.0, value))), BAR_H))
        # the population average as a tick across the bar
        tick = bar.left + round(BAR_W * min(1.0, average))
        pygame.draw.line(surface, theme.TEXT, (tick, bar.top - 2), (tick, bar.bottom + 2), 1)
        surface.blit(f.tiny.render(f"{value * 100:.0f}", True, theme.TEXT), (bar.right + 5, y))

    def _descent(self, surface, x, width, bottom, o: Organism,
                 descent: Descent | None) -> None:
        if descent is None:
            return
        f = self.fonts
        share = descent.line / descent.population * 100 if descent.population else 0.0
        # pinned to the bottom of the column so it doesnt move about as the
        # trait block grows and shrinks
        y = bottom - theme.PANEL_PAD - f.small.get_height() * 2 - 2
        surface.blit(f.small.render(f"line has {descent.line} alive ({share:.0f}%)",
                                    True, theme.TEXT_DIM), (x, y))
        surface.blit(f.small.render(f"{descent.descendants} descended from this one",
                                    True, theme.TEXT_DIM), (x, y + f.small.get_height() + 2))
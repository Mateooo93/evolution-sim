# the SELECTED panel. everything we know about the creature you clicked.
# this is my favourite bit of the whole UI: the bars show the genome and
# there is a little tick on each one showing where the POPULATION average
# is, so you can tell at a glance if this one is fast for its time or not

from typing import NamedTuple

import pygame

from simulation.genome import TRAIT_NAMES, body_radius_px, role_of
from simulation.types import Organism
from rendering.orbs import aggression_bucket, energy_level, make_orb, orb_color
from ui import theme
from ui.widgets import Meter, draw_panel

# Short display names for the genome traits.
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

CHIP = 34  # the portrait box
BAR_W = 54
BAR_H = 5


class Descent(NamedTuple):
    # family info for the selected one
    line: int          # how many of its line are alive
    descendants: int   # how many creatures came from this specific one
    population: int    # so we can do the %


class Inspector:
    def __init__(self, fonts) -> None:
        self.fonts = fonts
        # the little portrait orb, cached (it only changes when the
        # creature changes size/colour/brightness)
        self.meter = Meter(fonts.small, label_w=30, value_w=66)
        self._chip: pygame.Surface | None = None
        self._chip_key: tuple | None = None

    # drawing

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, o: Organism | None,
             config, averages: dict[str, float], descent: Descent | None) -> None:
        draw_panel(surface, rect)
        fonts = self.fonts
        x = rect.left + theme.PANEL_PAD
        y = rect.top + theme.PANEL_PAD
        surface.blit(fonts.title.render("SELECTED", True, theme.TEXT_DIM), (x, y))
        y += fonts.title.get_height() + 6

        if o is None:
            self._draw_empty(surface, rect, y)
            return

        y = self._draw_identity(surface, x, y, o, config)
        y = self._draw_meters(surface, rect, y, o, config)
        self._draw_traits(surface, rect, y, o, averages)
        self._draw_descent(surface, rect, o, descent)

    

    def _draw_empty(self, surface: pygame.Surface, rect: pygame.Rect, y: int) -> None:
        # nothing selected, just tell them what to do
        fonts = self.fonts
        lines = (
            ("click a creature", theme.TEXT_DIM),
            ("its genome, energy and", theme.TEXT_FAINT),
            ("family line land here.", theme.TEXT_FAINT),
        )
        for text, color in lines:
            rendered = fonts.small.render(text, True, color)
            surface.blit(rendered, (rect.left + theme.PANEL_PAD, y))
            y += fonts.small.get_height() + 1

    def _draw_identity(self, surface: pygame.Surface, x: int, y: int,
                       o: Organism, config) -> int:
        # portrait + "#412 gen 7" + the role and family line
        chip = pygame.Rect(x, y, CHIP, CHIP)
        pygame.draw.rect(surface, theme.BG, chip, border_radius=6)
        pygame.draw.rect(surface, theme.PANEL_BORDER, chip, width=1, border_radius=6)
        orb = self._portrait(o, config)
        surface.blit(orb, orb.get_rect(center=chip.center))

        fonts = self.fonts
        tx = chip.right + 10
        role = role_of(o.genome.aggression)
        role_color = {
            "predator": theme.PREDATOR,
            "mixed": theme.FOOD,
            "prey": theme.ACCENT,
        }[role]
        surface.blit(fonts.body.render(f"#{o.id}   gen {o.generation}", True, theme.TEXT),
                     (tx, y + 2))
        pygame.draw.circle(surface, role_color, (tx + 4, y + fonts.body.get_height() + 9), 3)
        tag = fonts.small.render(f"{role}   line #{o.lineage}", True, role_color)
        surface.blit(tag, (tx + 12, y + fonts.body.get_height() + 2))
        return y + CHIP + 8

    def _portrait(self, o: Organism, config) -> pygame.Surface:
        # draw the creature exactly like the plate does, so the dot in the
        # panel is the same dot you clicked on
        radius = max(3, round(body_radius_px(o.genome.size)))
        level = energy_level(o.energy, config.max_energy)
        agg = aggression_bucket(o.genome.aggression)
        key = (agg, radius, level)
        if key != self._chip_key:
            self._chip = make_orb(orb_color(agg / 7.0, level), radius, glow=3)
            self._chip_key = key
        return self._chip

    def _draw_meters(self, surface: pygame.Surface, rect: pygame.Rect, y: int,
                     o: Organism, config) -> int:
        fonts = self.fonts
        row = fonts.small.get_height() + 4
        left = rect.left + theme.PANEL_PAD
        width = rect.width - 2 * theme.PANEL_PAD
        life = config.base_lifespan + o.genome.lifespan * config.lifespan_range

        self.meter.draw(surface, pygame.Rect(left, y, width, row), "energy",
                        o.energy / config.max_energy,
                        f"{o.energy:3.0f}/{config.max_energy:.0f}")
        y += row
        age_frac = o.age / life if life > 0 else 0.0
        # Age is a countdown, so tint it as it runs out.
        age_color = theme.ACCENT if age_frac < 0.75 else theme.FOOD
        self.meter.draw(surface, pygame.Rect(left, y, width, row), "age",
                        age_frac, f"{o.age:3.0f}/{life:3.0f}s", age_color)
        y += row
        self.meter.draw(surface, pygame.Rect(left, y, width, row), "ready",
                        o.readiness, "yes" if o.readiness >= 1.0 else f"{o.readiness * 100:2.0f}%",
                        theme.PREDATOR if o.readiness >= 1.0 else theme.ACCENT_DIM)
        return y + row + 4

    def _draw_traits(self, surface: pygame.Surface, rect: pygame.Rect, y: int,
                     o: Organism, averages: dict[str, float]) -> None:
        # 8 traits, 2 columns of 4. averages[] is the population mean so we
        # can mark it on each bar
        fonts = self.fonts
        row = fonts.tiny.get_height() + 6
        col_w = (rect.width - 2 * theme.PANEL_PAD) // 2
        names = list(TRAIT_NAMES)
        for i, name in enumerate(names):
            col, line = divmod(i, 4)
            left = rect.left + theme.PANEL_PAD + col * col_w
            top = y + line * row
            self._trait(surface, left, top, name, getattr(o.genome, name), averages.get(name, 0.0))

    def _trait(self, surface: pygame.Surface, x: int, y: int, name: str,
               value: float, average: float) -> None:
        fonts = self.fonts
        surface.blit(fonts.tiny.render(TRAIT_LABELS[name], True, theme.TEXT_FAINT), (x, y))
        bar = pygame.Rect(x + 30, y + 2, BAR_W, BAR_H)
        pygame.draw.rect(surface, theme.METER_BG, bar, border_radius=2)
        fill = round(BAR_W * max(0.0, min(1.0, value)))
        if fill:
            pygame.draw.rect(surface, theme.ACCENT,
                             pygame.Rect(bar.left, bar.top, fill, BAR_H), border_radius=2)
        # the population average tick. this is the useful bit
        tick = bar.left + round(BAR_W * max(0.0, min(1.0, average)))
        pygame.draw.line(surface, theme.TEXT_DIM, (tick, bar.top - 3), (tick, bar.bottom + 1), 1)
        surface.blit(fonts.tiny.render(f"{value * 100:3.0f}", True, theme.TEXT),
                     (bar.right + 4, y))

    def _draw_descent(self, surface: pygame.Surface, rect: pygame.Rect,
                      o: Organism, descent: Descent | None) -> None:
        if descent is None:
            return
        fonts = self.fonts
        y = rect.bottom - theme.PANEL_PAD - fonts.small.get_height() * 2 - 2
        share = descent.line / descent.population * 100 if descent.population else 0.0
        line = fonts.small.render(
            f"line #{o.lineage}: {descent.line} alive ({share:.0f}% of plate)",
            True, theme.TEXT_DIM,
        )
        kids = fonts.small.render(
            f"descendants of #{o.id}: {descent.descendants}", True, theme.TEXT_DIM,
        )
        surface.blit(line, (rect.left + theme.PANEL_PAD, y))
        surface.blit(kids, (rect.left + theme.PANEL_PAD, y + fonts.small.get_height() + 2))

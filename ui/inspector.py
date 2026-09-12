"""Inspector panel: the hand-rolled UI that shows a selected organism.

Drawn entirely with pygame primitives (it is a "dumb view" like the
renderer — it reads an Organism and paints it). Used by main.py when the
user clicks a creature on the plate.
"""

import pygame

from simulation.genome import TRAIT_NAMES
from simulation.types import Organism
from ui import theme

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

BAR_W = 60  # trait bar width in px
COL_GAP = 14  # gap between the two trait columns
PAD = 10  # panel inner padding
ROW_H = 11  # vertical pitch per trait row

PANEL_W = 232
PANEL_H = 150
# Horizontal positions of the two trait columns (label, then bar).
COL1_LABEL = PAD
COL1_BAR = COL1_LABEL + 24 + 4
COL2_LABEL = COL1_BAR + BAR_W + COL_GAP
COL2_BAR = COL2_LABEL + 24 + 4


class Inspector:
    def __init__(self, font: pygame.font.Font):
        self.font = font

    def panel_rect(self, w: int, h: int) -> pygame.Rect:
        return pygame.Rect(12, h - PANEL_H - 12, PANEL_W, PANEL_H)

    def draw(self, surface: pygame.Surface, o: Organism, config) -> None:
        panel = self.panel_rect(*surface.get_size())
        pygame.draw.rect(surface, theme.PANEL, panel, border_radius=8)
        pygame.draw.rect(surface, theme.PANEL_BORDER, panel, width=1, border_radius=8)

        y = panel.top + 8

        # Role + id line.
        aggr = o.genome.aggression
        role = "predator" if aggr >= 0.7 else ("mix" if aggr >= 0.35 else "prey")
        role_color = theme.PREDATOR if aggr >= 0.35 else theme.ACCENT
        head = f"#{o.id}  gen {o.generation}  {role}"
        surface.blit(self.font.render(head, True, role_color), (panel.left + PAD, y))
        y += 15

        # Energy / age row.
        info = f"energy {o.energy:3.0f}/{config.max_energy:.0f}  age {o.age:4.0f}"
        surface.blit(self.font.render(info, True, theme.TEXT), (panel.left + PAD, y))
        y += 17

        # Genome trait bars, two per row: a label then a value bar in each
        # column, so all eight traits fit in four compact rows.
        names = list(TRAIT_NAMES)
        for i in range(0, len(names), 2):
            self._row(surface, panel, y, o, names[i], COL1_LABEL, COL1_BAR)
            if i + 1 < len(names):
                self._row(surface, panel, y, o, names[i + 1], COL2_LABEL, COL2_BAR)
            y += ROW_H

    def _row(self, surface: pygame.Surface, panel: pygame.Rect, y: int,
             o: Organism, name: str, lx: int, bx: int) -> None:
        """One labeled trait bar. `lx`/`bx` are panel-relative label and
        bar origins; the bar reflects the trait value on the organism."""
        label = TRAIT_LABELS[name]
        value = getattr(o.genome, name)
        surface.blit(self.font.render(label, True, theme.TEXT_DIM),
                     (panel.left + lx, y))
        self._bar(surface, panel.left + bx, y + 1, value)

    def _bar(self, surface: pygame.Surface, x: int, y: int, value: float) -> None:
        pygame.draw.rect(surface, theme.PANEL_BORDER, (x, y, BAR_W, 6), border_radius=3)
        fill = int(BAR_W * max(0.0, min(1.0, value)))
        if fill > 0:
            pygame.draw.rect(surface, theme.ACCENT, (x, y, fill, 6), border_radius=3)
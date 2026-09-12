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

BAR_W = 64  # trait bar width in px
BAR_H = 6  # trait bar height in px
COL_GAP = 16  # horizontal gap between the two trait columns
PAD = 12  # panel inner padding

PANEL_W = 240

# Horizontal origins (panel-relative) for the two trait columns.
# Each column: short label then a bar to its right.
COL_LABEL = (PAD, PAD + BAR_W + 40 + COL_GAP)
COL_BAR = (PAD + 36, PAD + BAR_W + 40 + COL_GAP + 36)


class Inspector:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        # Row and line pitch derive from the real glyph height so rows of
        # text never overlap, whatever the face metrics happen to be.
        self.line_h = self.font.get_height() + 2
        self.row_h = self.font.get_height() + 4
        self.panel_h = PAD + 2 * self.line_h + 4 * self.row_h + 8

    def panel_rect(self, w: int, h: int) -> pygame.Rect:
        return pygame.Rect(12, h - self.panel_h - 12, PANEL_W, self.panel_h)

    def draw(self, surface: pygame.Surface, o: Organism, config) -> None:
        panel = self.panel_rect(*surface.get_size())
        pygame.draw.rect(surface, theme.PANEL, panel, border_radius=8)
        pygame.draw.rect(surface, theme.PANEL_BORDER, panel, width=1, border_radius=8)

        x0 = panel.left + PAD
        y = panel.top + PAD

        # Role + id line.
        aggr = o.genome.aggression
        role = "predator" if aggr >= 0.7 else ("mix" if aggr >= 0.35 else "prey")
        role_color = theme.PREDATOR if aggr >= 0.35 else theme.ACCENT
        head = f"#{o.id}  gen {o.generation}  {role}"
        surface.blit(self.font.render(head, True, role_color), (x0, y))
        y += self.line_h

        # Energy / age row.
        info = f"energy {o.energy:3.0f}/{config.max_energy:.0f}  age {o.age:4.0f}"
        surface.blit(self.font.render(info, True, theme.TEXT), (x0, y))
        y += self.line_h + 2

        # Genome trait bars, two per row.
        names = list(TRAIT_NAMES)
        for i in range(0, len(names), 2):
            c1 = names[i]
            c2 = names[i + 1] if i + 1 < len(names) else None
            # column 1
            self._trait(surface, panel, y, o, c1, COL_LABEL[0], COL_BAR[0])
            # column 2
            if c2 is not None:
                self._trait(surface, panel, y, o, c2, COL_LABEL[1], COL_BAR[1])
            y += self.row_h

    def _trait(self, surface: pygame.Surface, panel: pygame.Rect, y: int,
               o: Organism, name: str, lx: int, bx: int) -> None:
        """One labeled trait bar. `lx`/`bx` are panel-relative origins."""
        label = TRAIT_LABELS[name]
        value = getattr(o.genome, name)
        surface.blit(self.font.render(label, True, theme.TEXT_DIM),
                     (panel.left + lx, y))
        self._bar(surface, panel.left + bx, y + (self.font.get_height() - BAR_H) // 2, value)

    def _bar(self, surface: pygame.Surface, x: int, y: int, value: float) -> None:
        pygame.draw.rect(surface, theme.PANEL_BORDER, (x, y, BAR_W, BAR_H), border_radius=3)
        fill = int(BAR_W * max(0.0, min(1.0, value)))
        if fill > 0:
            pygame.draw.rect(surface, theme.ACCENT, (x, y, fill, BAR_H), border_radius=3)
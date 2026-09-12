"""Inspector panel: the hand-rolled UI that shows a selected organism.

Drawn entirely with pygame primitives (it is a "dumb view" like the
renderer — it reads an Organism and paints it). Used by main.py when the
user clicks a creature on the plate.
"""

import pygame

from simulation.genome import TRAIT_NAMES, body_radius_px, move_speed_px
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

BAR_W = 84  # trait bar width in px


class Inspector:
    def __init__(self, font: pygame.font.Font):
        self.font = font

    def panel_rect(self, w: int, h: int) -> pygame.Rect:
        return pygame.Rect(12, h - 158, 236, 146)

    def draw(self, surface: pygame.Surface, o: Organism, config) -> None:
        panel = self.panel_rect(*surface.get_size())
        pygame.draw.rect(surface, theme.PANEL, panel, border_radius=8)
        pygame.draw.rect(surface, theme.PANEL_BORDER, panel, width=1, border_radius=8)

        x = panel.left + 10
        y = panel.top + 8

        # Role + id line.
        aggr = o.genome.aggression
        role = "predator" if aggr >= 0.7 else ("mix" if aggr >= 0.35 else "prey")
        role_color = theme.PREDATOR if aggr >= 0.35 else theme.ACCENT
        head = f"#{o.id}  gen {o.generation}  {role}"
        surface.blit(self.font.render(head, True, role_color), (x, y))
        y += 14

        # Energy / age row.
        info = f"energy {o.energy:3.0f}/{config.max_energy:.0f}  age {o.age:4.0f}"
        surface.blit(self.font.render(info, True, theme.TEXT), (x, y))
        y += 18

        # Genome trait bars, two per row.
        names = list(TRAIT_NAMES)
        bar_x = x + 34
        row_h = 10
        for i in range(0, len(names), 2):
            for name in names[i:i + 2]:
                lbl = TRAIT_LABELS[name]
                surface.blit(self.font.render(lbl, True, theme.TEXT_DIM), (bar_x, y))
                val = getattr(o.genome, name)
                self._bar(surface, bar_x + 22, y - 1, val)
                bar_x += 100
            bar_x = x + 34
            y += row_h

    def _bar(self, surface: pygame.Surface, x: int, y: int, value: float) -> None:
        pygame.draw.rect(surface, theme.PANEL_BORDER, (x, y, BAR_W, 6), border_radius=3)
        fill = int(BAR_W * max(0.0, min(1.0, value)))
        if fill > 0:
            pygame.draw.rect(surface, theme.ACCENT, (x, y, fill, 6), border_radius=3)
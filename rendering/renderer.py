"""Draws the ecosystem onto a pygame surface.

The renderer is a dumb view: it reads simulation state and paints it.
The static background (fill + grid) is pre-rendered once and blitted
every frame, so the per-frame cost is one blit plus the organisms.
"""

import math

import pygame

from simulation.ecosystem import Ecosystem
from ui import theme

GRID_SPACING = 64
ORGANISM_RADIUS = 3
HEADING_TICK = 8


class Renderer:
    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        w, h = surface.get_size()
        self.background = self._build_background(w, h)

    def _build_background(self, w: int, h: int) -> pygame.Surface:
        bg = pygame.Surface((w, h))
        bg.fill(theme.BG)

        grid = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(0, w + 1, GRID_SPACING):
            pygame.draw.line(grid, (*theme.TEXT_DIM, theme.GRID_ALPHA), (x, 0), (x, h))
        for y in range(0, h + 1, GRID_SPACING):
            pygame.draw.line(grid, (*theme.TEXT_DIM, theme.GRID_ALPHA), (0, y), (w, y))
        bg.blit(grid, (0, 0))
        return bg

    def render(self, world: Ecosystem) -> None:
        self.surface.blit(self.background, (0, 0))

        for o in world.organisms:
            # heading tick so you can see where each dot is going
            pygame.draw.line(
                self.surface,
                theme.HEADING,
                (o.x, o.y),
                (o.x + math.cos(o.heading) * HEADING_TICK,
                 o.y + math.sin(o.heading) * HEADING_TICK),
                1,
            )
            pygame.draw.circle(
                self.surface, theme.ACCENT, (int(o.x), int(o.y)), ORGANISM_RADIUS
            )

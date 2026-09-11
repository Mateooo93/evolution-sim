"""Draws the ecosystem onto a pygame surface.

The renderer is a dumb view: it reads simulation state and paints it.
The static background (fill + grid) is pre-rendered once and blitted
every frame, so the per-frame cost is one blit plus the organisms.

Traits are drawn directly, so selection is visible on the plate:
    size       -> body radius
    energy     -> body brightness (dim = starving)
    speed      -> heading tick length
"""

import math

import pygame

from simulation.ecosystem import Ecosystem
from simulation.genome import body_radius_px
from ui import theme

GRID_SPACING = 64
STARVED = (30, 90, 62)  # color at zero energy
MAX_TICK = 14  # px at max speed


def _energy_color(energy: float, max_energy: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, energy / max_energy))
    return tuple(
        round(starved + (accent - starved) * t)
        for starved, accent in zip(STARVED, theme.ACCENT)
    )


class Renderer:
    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.font = pygame.font.SysFont("dejavusansmono,consolas,monospace", 10)
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

        # Food under the organisms
        for f in world.food:
            pygame.draw.circle(self.surface, theme.FOOD, (int(f.x), int(f.y)), 3)

        for o in world.organisms:
            radius = body_radius_px(o.genome.size)
            tick = 4 + o.genome.speed * MAX_TICK  # 4..18 px

            # heading tick: length encodes speed
            pygame.draw.line(
                self.surface,
                theme.HEADING,
                (o.x, o.y),
                (o.x + math.cos(o.heading) * tick,
                 o.y + math.sin(o.heading) * tick),
                1,
            )
            # body: radius encodes size, brightness encodes energy
            pygame.draw.circle(
                self.surface,
                _energy_color(o.energy, world.config.max_energy),
                (int(o.x), int(o.y)),
                round(radius),
            )
            # ready to mate: a thin ring around the body
            if o.readiness >= 1.0:
                pygame.draw.circle(
                    self.surface,
                    theme.ACCENT,
                    (int(o.x), int(o.y)),
                    round(radius) + 2,
                    1,
                )

        self._draw_history(world)

    def _draw_history(self, world: Ecosystem) -> None:
        """Bottom-right sparklines: population (accent) and avg speed (dim)."""
        hist = world.history
        if len(hist) < 2:
            return
        w, h = self.surface.get_size()
        panel = pygame.Rect(w - 196, h - 80, 184, 68)
        pygame.draw.rect(self.surface, theme.PANEL, panel, border_radius=6)
        pygame.draw.rect(self.surface, theme.PANEL_BORDER, panel, width=1, border_radius=6)

        plot = panel.inflate(-12, -30)
        n = len(hist)
        pop_scale = float(world.config.max_population)

        def polyline(key: int, scale: float, color: tuple[int, int, int]) -> None:
            pts = []
            for i, sample in enumerate(hist):
                x = plot.left + (i / (n - 1)) * plot.width
                y = plot.bottom - min(1.0, sample[key] / scale) * plot.height
                pts.append((x, y))
            pygame.draw.lines(self.surface, color, False, pts, 1)

        polyline(3, pop_scale, theme.ACCENT)  # population
        polyline(1, 1.0, theme.TEXT_DIM)  # avg speed

        self.surface.blit(self.font.render("pop", True, theme.ACCENT),
                          (panel.left + 6, panel.bottom - 13))
        self.surface.blit(self.font.render("avg spd", True, theme.TEXT_DIM),
                          (panel.left + 40, panel.bottom - 13))

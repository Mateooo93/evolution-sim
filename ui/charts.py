

import pygame

from simulation.ecosystem import Sample
from ui import theme

PAD = 4
WINDOW = 300  


_shade = None


def _shade_for(size):
    global _shade
    if _shade is None or _shade.get_size() != size:
        _shade = pygame.Surface(size, pygame.SRCALPHA)
    _shade.fill((0, 0, 0, 0))
    return _shade


def draw_trends(surface: pygame.Surface, rect: pygame.Rect, hist: list[Sample],
                fonts, config) -> None:
    legend_h = fonts.small.get_height() + 2
    plot = pygame.Rect(rect.left, rect.top, rect.width, rect.height - legend_h)
    pygame.draw.rect(surface, theme.BG, plot)

    if len(hist) < 2:
        text = fonts.tiny.render("waiting for data", True, theme.TEXT_FAINT)
        surface.blit(text, text.get_rect(center=plot.center))
    else:
        window = hist[-WINDOW:]
        n = len(window)

        # a couple of faint lines across so you can judge how big a swing is
        for i in (1, 2):
            y = plot.top + round(plot.height * i / 3)
            pygame.draw.line(surface, theme.PANEL_BORDER, (plot.left, y), (plot.right, y), 1)

        def line(values, scale, color, fill=False):
            if scale <= 0:
                return
            pts = [(plot.left + round(i * (plot.width - 1) / max(1, n - 1)),
                    plot.bottom - 1 - round(min(1.0, values[i] / scale) * (plot.height - 2)))
                   for i in range(n)]
            if fill:
                shade = _shade_for(plot.size)
                poly = [(p[0] - plot.left, p[1] - plot.top) for p in pts]
                poly += [(poly[-1][0], plot.height), (poly[0][0], plot.height)]
                pygame.draw.polygon(shade, (*color, 40), poly)
                surface.blit(shade, plot.topleft)
            pygame.draw.lines(surface, color, False, pts, 1)

        line([s.population for s in window], config.max_population * 0.65,
             theme.ACCENT, fill=True)
        line([s.food for s in window], config.max_food * 0.65, theme.FOOD)
        line([s.aggression for s in window], 1.0, theme.PREDATOR)

    # current values in their own colours, no dots or boxes
    if not hist:
        return
    last = hist[-1]
    y = rect.bottom - legend_h
    x = rect.left
    for text, color in ((f"pop {last.population}", theme.ACCENT),
                        (f"food {last.food}", theme.FOOD),
                        (f"agg {last.aggression * 100:.0f}%", theme.PREDATOR)):
        rendered = fonts.small.render(text, True, color)
        surface.blit(rendered, (x, y))
        x += rendered.get_width() + 12

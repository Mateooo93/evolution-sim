"""The trends chart: the ecosystem's vital signs over the run.

Three quantities share one plot because they are read together — the
population trace against the food supply (who is eating whom out of
house and home) and against mean aggression (the arms race). Each series
is normalised to its own range, so the point is shape rather than
absolute units, and the legend carries the current value of each line.
"""

import pygame

from simulation.ecosystem import Sample
from ui import theme

PAD = 6
GRID_LINES = 3
WINDOW = 300  # seconds of history shown (the sim keeps 600)

# Semi-transparent surface reused for the fill under the population line;
# allocating one per frame would churn a full plot-sized buffer at 60 Hz.
_shade: pygame.Surface | None = None


def _shade_for(size: tuple[int, int]) -> pygame.Surface:
    global _shade
    if _shade is None or _shade.get_size() != size:
        _shade = pygame.Surface(size, pygame.SRCALPHA)
    _shade.fill((0, 0, 0, 0))
    return _shade


def draw_trends(
    surface: pygame.Surface,
    rect: pygame.Rect,
    hist: list[Sample],
    fonts,
    config,
) -> None:
    """Plot population, food and aggression inside `rect`, legend included."""
    legend_h = fonts.small.get_height() + 2
    plot = pygame.Rect(rect.left, rect.top, rect.width, rect.height - legend_h)
    pygame.draw.rect(surface, theme.BG, plot, border_radius=4)

    if len(hist) < 2:
        hint = fonts.small.render("collecting data…", True, theme.TEXT_FAINT)
        surface.blit(hint, hint.get_rect(center=plot.center))
    else:
        window = hist[-WINDOW:]
        n = len(window)

        # Horizontal grid: with every series normalised, the grid is what
        # shows the size of the swing.
        for i in range(1, GRID_LINES + 1):
            y = plot.top + round(plot.height * i / (GRID_LINES + 1))
            pygame.draw.line(surface, theme.PANEL_BORDER, (plot.left, y), (plot.right, y), 1)

        def plot_line(values: list[float], scale: float,
                      color: tuple[int, int, int], fill: bool = False) -> None:
            if scale <= 0:
                return
            pts = [
                (
                    plot.left + round(i * (plot.width - 1) / max(1, n - 1)),
                    plot.bottom - 1 - round(min(1.0, values[i] / scale) * (plot.height - 2)),
                )
                for i in range(n)
            ]
            if fill:
                shade = _shade_for(plot.size)
                poly = [(p[0] - plot.left, p[1] - plot.top) for p in pts]
                poly += [(poly[-1][0], plot.height), (poly[0][0], plot.height)]
                pygame.draw.polygon(shade, (*color, 34), poly)
                surface.blit(shade, plot.topleft)
            pygame.draw.lines(surface, color, False, pts, 1)

        plot_line([s.population for s in window],
                  float(config.max_population) * 0.65, theme.ACCENT, fill=True)
        plot_line([s.food for s in window], float(config.max_food) * 0.65, theme.FOOD)
        plot_line([s.aggression for s in window], 1.0, theme.PREDATOR)

    # Legend: swatch, name, and the live value of each series.
    y = rect.bottom - legend_h // 2
    x = rect.left + 2
    latest = hist[-1] if hist else None
    for label, value, color in (
        ("pop", str(latest.population) if latest else "-", theme.ACCENT),
        ("food", str(latest.food) if latest else "-", theme.FOOD),
        ("agg", f"{latest.aggression * 100:.0f}%" if latest else "-", theme.PREDATOR),
    ):
        pygame.draw.circle(surface, color, (x + 3, y - 1), 3)
        text = fonts.small.render(f"{label} {value}", True, theme.TEXT_DIM)
        surface.blit(text, text.get_rect(midleft=(x + 10, y)))
        x += 10 + text.get_width() + 12

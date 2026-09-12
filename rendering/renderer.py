"""Draws the ecosystem onto a pygame surface.

The renderer is a dumb view: it reads simulation state and paints it.
The static background (fill + grid) is pre-rendered once and blitted
every frame, so the per-frame cost is one blit plus the organisms.

Organisms are drawn from a pre-rendered "orb atlas": antialiased radial
sprites baked at init for every (species, radius, energy-brightness)
combination, so the per-frame cost is a single blit per organism with
smooth soft-edged cells. Traits are still visible on the plate:
    size       -> body radius
    energy     -> body brightness (dim = starving)
    speed      -> heading tick length
    aggression -> species colour (prey = green, predator = red)
"""

import math

import pygame

from simulation.ecosystem import Ecosystem
from simulation.genome import body_radius_px
from simulation.types import Organism
from ui import theme

GRID_SPACING = 64
MAX_TICK = 14  # px at max speed
RADIUS_STEPS = list(range(2, 9))  # rounded body radii (2..8 px)
ENERGY_LEVELS = 8  # brightness buckets for the atlas
AGGRESSION_BUCKETS = 8  # colour buckets for the aggression spectrum
GLOW = 2  # px of soft halo around each orb
TRAIL_LEN = 10  # how many recent positions make up a movement tail

# Colors at zero energy (dim) for each species.
_STARVED_PREY = (30, 90, 62)
_STARVED_PRED = (94, 38, 38)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(av + (bv - av) * t) for av, bv in zip(a, b))


def _orb_color(species: str, level: int) -> tuple[int, int, int]:
    """Body color for an atlas cell: brightness rises with the energy level."""
    t = level / (ENERGY_LEVELS - 1) if ENERGY_LEVELS > 1 else 1.0
    if species == "pred":
        return _lerp(_STARVED_PRED, theme.PREDATOR, t)
    return _lerp(_STARVED_PREY, theme.ACCENT, t)


def _aggression_color(aggression: float, level: int) -> tuple[int, int, int]:
    """Body color across the aggression spectrum: herbivore green at low
    aggression, shifting through amber to carnivore red at high aggression.
    The energy level still controls brightness (dim = starving).
    """
    t = min(1.0, max(0.0, aggression))
    green = _orb_color("prey", level)
    red = _orb_color("pred", level)
    warm = _lerp(green, red, 0.45)  # amber midpoint
    if t < 0.5:
        return _lerp(green, warm, t * 2.0)
    return _lerp(warm, red, (t - 0.5) * 2.0)


def _make_orb(color: tuple[int, int, int], radius: int, glow: int = GLOW) -> pygame.Surface:
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
    core = _lerp(color, (255, 255, 255), 0.35)
    pygame.draw.circle(surf, (*core, 220), (c, c), max(1, int(radius * 0.7)))
    inner = _lerp(color, (255, 255, 255), 0.65)
    pygame.draw.circle(surf, (*inner, 160), (c, c), max(1, int(radius * 0.4)))
    return surf


class Renderer:
    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.font = pygame.font.SysFont("dejavusansmono,consolas,monospace", 10)
        w, h = surface.get_size()
        self.background = self._build_background(w, h)
        self.atlas: dict[tuple[int, int, int], pygame.Surface] = {
            (agg, radius, lvl): _make_orb(
                _aggression_color(agg / (AGGRESSION_BUCKETS - 1), lvl), radius
            )
            for agg in range(AGGRESSION_BUCKETS)
            for radius in RADIUS_STEPS
            for lvl in range(ENERGY_LEVELS)
        }
        self.food_sprite = _make_orb(theme.FOOD, 3, glow=1)
        # Movement trails (a render-side channel, keyed by organism id):
        # each live organism leaves a short fading tail so the plate reads
        # as alive and hunting is legible. Not part of the simulation.
        self.trails: dict[int, list[tuple[float, float]]] = {}

    def _build_background(self, w: int, h: int) -> pygame.Surface:
        bg = pygame.Surface((w, h))
        bg.fill(theme.BG)

        # A soft radial vignette: a darker frame fading in toward a clear centre,
        # giving the plate depth so blank space doesn't read as "empty".
        side = 128
        glow = pygame.Surface((side, side), pygame.SRCALPHA)
        cc = side // 2
        # Paint filled circles from the rim inward, each inner circle a bit
        # lighter, so darkness accumulates at the edge and the middle stays
        # clear.
        for rr in range(cc, 0, -4):
            a = int(210 * (rr / cc))
            pygame.draw.circle(glow, (0, 0, 0, a), (cc, cc), rr)
        glow = pygame.transform.smoothscale(glow, (w, h))
        bg.blit(glow, (0, 0))

        grid = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(0, w + 1, GRID_SPACING):
            pygame.draw.line(grid, (*theme.TEXT_DIM, theme.GRID_ALPHA), (x, 0), (x, h))
        for y in range(0, h + 1, GRID_SPACING):
            pygame.draw.line(grid, (*theme.TEXT_DIM, theme.GRID_ALPHA), (0, y), (w, y))
        bg.blit(grid, (0, 0))
        return bg

    def _update_trails(self, world: Ecosystem) -> None:
        """Append each living organism's current position to its trail and
        drop trails for organisms that died. Trail points are kept short."""
        seen = set()
        for o in world.organisms:
            seen.add(o.id)
            trail = self.trails.get(o.id)
            if trail is None:
                self.trails[o.id] = [(o.x, o.y)]
                continue
            trail.append((o.x, o.y))
            if len(trail) > TRAIL_LEN:
                del trail[0]
        for oid in [k for k in self.trails if k not in seen]:
            del self.trails[oid]

    def _draw_trails(self, world: Ecosystem) -> None:
        """A fading tail per organism, tinted by its aggression, so motion
        and hunting are readable even against the dark plate."""
        by_id = {o.id: o for o in world.organisms}
        for oid, pts in self.trails.items():
            o = by_id.get(oid)
            if o is None or len(pts) < 2:
                continue
            color = _lerp(theme.HEADING, theme.HEADING_PRED, o.genome.aggression)
            n = len(pts)
            for i in range(n - 1):
                # Older segments blend toward the background: a real fade.
                seg = _lerp(color, theme.BG, 1.0 - (i / n))
                pygame.draw.line(self.surface, seg,
                                 (int(pts[i][0]), int(pts[i][1])),
                                 (int(pts[i + 1][0]), int(pts[i + 1][1])), 1)

    def render(self, world: Ecosystem, selected: Organism | None = None,
           snapshot: dict | None = None) -> None:
        """Draw the scene. If a `snapshot` (from simulation.snapshot) is
        given it is rendered instead of the live world — used by the
        time-machine replay. Background and history chart stay live."""
        self.surface.blit(self.background, (0, 0))

        food = world.food if snapshot is None else snapshot["food"]
        organisms = world.organisms if snapshot is None else snapshot["organisms"]
        live = snapshot is None  # trails only make sense on the live world

        # Food under the organisms (a soft amber orb, consistent with the cells)
        fs = self.food_sprite.get_width() // 2
        for f in food:
            self.surface.blit(self.food_sprite, (int(f.x) - fs, int(f.y) - fs))

        if live:
            self._update_trails(world)
            self._draw_trails(world)

        selected_pos: tuple[float, float] | None = None
        for o in organisms:
            radius = body_radius_px(o.genome.size)
            tick = 4 + o.genome.speed * MAX_TICK  # 4..18 px
            aggression = o.genome.aggression
            tick_color = _lerp(theme.HEADING, theme.HEADING_PRED, aggression)

            # heading tick: a short directional notch under the body
            pygame.draw.line(
                self.surface,
                tick_color,
                (o.x, o.y),
                (o.x + math.cos(o.heading) * tick,
                 o.y + math.sin(o.heading) * tick),
                1,
            )
            # body: pre-rendered orb (aggression + radius + energy brightness)
            lvl = min(
                ENERGY_LEVELS - 1,
                max(0, int(o.energy / world.config.max_energy * ENERGY_LEVELS)),
            )
            agg = min(
                AGGRESSION_BUCKETS - 1,
                max(0, int(aggression * AGGRESSION_BUCKETS)),
            )
            orb = self.atlas[(agg, round(radius), lvl)]
            self.surface.blit(orb, (int(o.x) - orb.get_width() // 2,
                                    int(o.y) - orb.get_height() // 2))

            # ready to mate: a thin ring around the body
            if o.readiness >= 1.0:
                ring = _lerp(theme.ACCENT, theme.PREDATOR, aggression)
                pygame.draw.circle(
                    self.surface,
                    ring,
                    (int(o.x), int(o.y)),
                    round(radius) + 2,
                    1,
                )
            if selected is not None and o.id == selected.id:
                selected_pos = (o.x, o.y)

        # Selection ring: bright and slightly larger, drawn last so it sits on top.
        if selected is not None and selected_pos is not None:
            r = round(body_radius_px(selected.genome.size)) + 4
            pygame.draw.circle(self.surface, (255, 255, 255),
                               (int(selected_pos[0]), int(selected_pos[1])), r, 2)
            pygame.draw.circle(self.surface, theme.ACCENT,
                               (int(selected_pos[0]), int(selected_pos[1])), r + 2, 1)

        self._draw_history(world)

    def _draw_history(self, world: Ecosystem) -> None:
        """Bottom-right chart: population, avg speed and avg aggression over
        the last few minutes, each drawn in its own way so the arms race is
        readable at a glance."""
        hist = world.history
        if len(hist) < 2:
            return
        w, h = self.surface.get_size()
        panel = pygame.Rect(w - 196, h - 84, 184, 74)
        pygame.draw.rect(self.surface, theme.PANEL, panel, border_radius=6)
        pygame.draw.rect(self.surface, theme.PANEL_BORDER, panel, width=1, border_radius=6)

        title_y = panel.top + 8
        self.surface.blit(self.font.render("pop / speed / aggression", True, theme.TEXT_DIM),
                          (panel.left + 6, title_y))

        plot = panel.inflate(-12, -38).move(0, 16)
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
        polyline(4, 1.0, theme.PREDATOR)  # avg aggression

        # Legend (3 dots + labels along the bottom of the panel).
        legend_y = panel.bottom - 10
        items = (("pop", theme.ACCENT), ("spd", theme.TEXT_DIM), ("agg", theme.PREDATOR))
        x = panel.left + 6
        for label, color in items:
            pygame.draw.circle(self.surface, color, (x + 3, legend_y), 2)
            x += 8
            self.surface.blit(self.font.render(label, True, color), (x, legend_y - 5))
            x += self.font.size(label)[0] + 10

    def draw_selected_banner(self, o: Organism, font: pygame.font.Font) -> None:
        """A small readout pinned under the selected organism with its id."""
        self.surface.blit(font.render(f"#{o.id}", True, (255, 255, 255)),
                          (int(o.x) - 8, int(o.y) + 6))
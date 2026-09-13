# everything that gets painted on the plate.
# this is a "dumb" view: it reads the world and draws it, it never changes
# anything. the plate has its own surface and main.py blits it into place,
# that way the sim has no clue where it is on screen

import math

import pygame

from rendering.orbs import (
    AGGRESSION_BUCKETS,
    ENERGY_LEVELS,
    GLOW,
    RADIUS_STEPS,
    aggression_bucket,
    energy_level,
    lerp,
    make_orb,
    orb_color,
)
from simulation.ecosystem import Ecosystem
from simulation.genome import body_radius_px
from simulation.types import Event, Organism
from ui import theme
from ui.fonts import MONO, load_font

GRID_SPACING = 64
MAX_TICK = 14   # px, at full speed
TRAIL_LEN = 10  # how many old positions make the tail

# the rings you get when something happens. (colour, how long it lives,
# how big it grows). ate = a meal, eaten = a kill, arrived = an immigrant
PULSES = {
    "ate": (theme.FOOD_HI, 0.35, 26.0),
    "eaten": (theme.PREDATOR, 0.55, 40.0),
    "arrived": (theme.TEXT, 0.6, 34.0),
}


class Renderer:
    def __init__(self, size: tuple[int, int]) -> None:
        self.surface = pygame.Surface(size)
        self.font = load_font(MONO, 10)
        w, h = size
        self.background = self._build_background(w, h)
        # pre-render every possible orb up front so drawing a creature
        # later is one blit. 8 x 7 x 8 combinations, only takes a sec
        self.atlas: dict[tuple[int, int, int], pygame.Surface] = {
            (agg, radius, lvl): make_orb(orb_color(agg / (AGGRESSION_BUCKETS - 1), lvl), radius)
            for agg in range(AGGRESSION_BUCKETS)
            for radius in RADIUS_STEPS
            for lvl in range(ENERGY_LEVELS)
        }
        self.food_sprite = make_orb(theme.FOOD, 3, glow=1)
        # tails, keyed by creature id. this is pure decoration, the sim
        # doesnt know they exist
        self.trails: dict[int, list[tuple[float, float]]] = {}
        # (x, y, time left, total life, colour, how far it grows)
        self.pulses: list[tuple[float, float, float, float, tuple[int, int, int], float]] = []

    def _build_background(self, w: int, h: int) -> pygame.Surface:
        # done once at startup then blitted every frame, way cheaper
        bg = pygame.Surface((w, h))
        bg.fill(theme.BG)

        # the vignette: dark round the edges fading to clear in the middle
        # so the empty space looks like depth and not just black nothing
        side = 128
        glow = pygame.Surface((side, side), pygame.SRCALPHA)
        cc = side // 2
        for rr in range(cc, 0, -4):
            a = int(210 * (rr / cc))
            pygame.draw.circle(glow, (0, 0, 0, a), (cc, cc), rr)
        bg.blit(pygame.transform.smoothscale(glow, (w, h)), (0, 0))

        grid = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(0, w + 1, GRID_SPACING):
            pygame.draw.line(grid, (*theme.TEXT_DIM, theme.GRID_ALPHA), (x, 0), (x, h))
        for y in range(0, h + 1, GRID_SPACING):
            pygame.draw.line(grid, (*theme.TEXT_DIM, theme.GRID_ALPHA), (0, y), (w, y))
        bg.blit(grid, (0, 0))
        return bg

    def consume(self, events: list[Event]) -> None:
        # main.py hands us this frames events, we turn them into rings
        for e in events:
            look = PULSES.get(e.kind)
            if look is not None:
                color, life, grow = look
                self.pulses.append((e.x, e.y, life, life, color, grow))

    def _age_pulses(self, dt: float) -> None:
        if not self.pulses:
            return
        kept = []
        for x, y, left, life, color, grow in self.pulses:
            left -= dt
            if left > 0.0:
                kept.append((x, y, left, life, color, grow))
        self.pulses = kept

    def _draw_pulses(self) -> None:
        # expanding ring that fades out. t goes 1 -> 0 over its life
        for x, y, left, life, color, grow in self.pulses:
            t = left / life
            radius = round((1.0 - t) * grow) + 3
            pygame.draw.circle(
                self.surface, (*color, int(190 * t)), (int(x), int(y)),
                radius, max(1, int(1 + t * 2)),
            )

    def _update_trails(self, world: Ecosystem) -> None:
        # add this frame position to everyones tail, forget the dead.
        # if someone wrapped round the edge we clear their tail instead of
        # drawing a line straight across the whole screen (that looked
        # terrible, took me a while to work out what was causing it)
        half_w = world.config.width / 2
        half_h = world.config.height / 2
        seen = set()
        for o in world.organisms:
            seen.add(o.id)
            trail = self.trails.get(o.id)
            if trail is None:
                self.trails[o.id] = [(o.x, o.y)]
                continue
            lx, ly = trail[-1]
            if abs(o.x - lx) > half_w or abs(o.y - ly) > half_h:
                trail.clear()
            trail.append((o.x, o.y))
            if len(trail) > TRAIL_LEN:
                del trail[0]
        for oid in [k for k in self.trails if k not in seen]:
            del self.trails[oid]

    def _draw_trails(self, world: Ecosystem) -> None:
        # a short tail so you can read where things are going. tinted by
        # aggression so a hunt is a red streak chasing a green one.
        # TWO lines per creature not one per segment - the old way spent
        # most of the frame budget in here and tanked it to 55fps
        by_id = {o.id: o for o in world.organisms}
        n_segments = 0  # left over from when i was profiling this
        for oid, pts in self.trails.items():
            o = by_id.get(oid)
            if o is None or len(pts) < 2:
                continue
            color = lerp(theme.HEADING, theme.HEADING_PRED, o.genome.aggression)
            if len(pts) > 4:
                pygame.draw.lines(self.surface, lerp(color, theme.BG, 0.6), False, pts, 1)
                pygame.draw.lines(self.surface, lerp(color, theme.BG, 0.2), False, pts[-4:], 1)
            else:
                pygame.draw.lines(self.surface, lerp(color, theme.BG, 0.4), False, pts, 1)
            n_segments += len(pts)

    def render(self, world: Ecosystem, selected: Organism | None = None,
               kin: frozenset[int] = frozenset(), snapshot: dict | None = None,
               dt: float = 1 / 60) -> None:
        # draw the world. if we get a snapshot we draw that instead (thats
        # the time machine). snapshots have no tails or pulses, theyre only
        # a copy of positions anyway
        self.surface.blit(self.background, (0, 0))

        food = world.food if snapshot is None else snapshot["food"]
        organisms = world.organisms if snapshot is None else snapshot["organisms"]
        live = snapshot is None

        # food goes UNDER the creatures
        fs = self.food_sprite.get_width() // 2
        for f in food:
            self.surface.blit(self.food_sprite, (int(f.x) - fs, int(f.y) - fs))

        if live:
            self._update_trails(world)
            self._draw_trails(world)
            self._age_pulses(dt)
            self._draw_pulses()

        # family rings first so they sit behind the herd
        if selected is not None and kin:
            self._draw_kin(organisms, kin, selected.id)

        selected_pos: tuple[float, float] | None = None
        for o in organisms:
            self._draw_organism(o, world.config.max_energy)
            if selected is not None and o.id == selected.id:
                selected_pos = (o.x, o.y)

        if selected is not None and selected_pos is not None:
            self._draw_reticle(selected_pos, body_radius_px(selected.genome.size), selected.id)

    def _draw_organism(self, o: Organism, max_energy: float) -> None:
        radius = body_radius_px(o.genome.size)
        tick = 4 + o.genome.speed * MAX_TICK  # 4..18 px
        aggression = o.genome.aggression
        tick_color = lerp(theme.HEADING, theme.HEADING_PRED, aggression)

        # the little line showing which way its facing. longer = faster
        pygame.draw.line(
            self.surface,
            tick_color,
            (o.x, o.y),
            (o.x + math.cos(o.heading) * tick, o.y + math.sin(o.heading) * tick),
            1,
        )
        orb = self.atlas[
            (aggression_bucket(aggression), round(radius),
             energy_level(o.energy, max_energy))
        ]
        self.surface.blit(orb, (int(o.x) - orb.get_width() // 2,
                                int(o.y) - orb.get_height() // 2))

        # thin ring = ready to breed
        if o.readiness >= 1.0:
            ring = lerp(theme.ACCENT, theme.PREDATOR, aggression)
            pygame.draw.circle(self.surface, ring, (int(o.x), int(o.y)),
                               round(radius) + 2, 1)

    def _draw_kin(self, organisms, kin: frozenset[int], selected_id: int) -> None:
        # dim ring on every living member of the selected creatures family
        # line. you can sit and watch a family take over the plate
        for o in organisms:
            if o.id in kin and o.id != selected_id:
                pygame.draw.circle(
                    self.surface, theme.ACCENT_DIM, (int(o.x), int(o.y)),
                    round(body_radius_px(o.genome.size)) + 3, 1,
                )

    def _draw_reticle(self, pos: tuple[float, float], radius: float, oid: int) -> None:
        # brackets round whatever you clicked + its id so you can find it
        # again after it wanders off
        x, y = int(pos[0]), int(pos[1])
        r = round(radius) + 7
        pygame.draw.circle(self.surface, (255, 255, 255), (x, y), r, 1)
        arm = 5
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            cx, cy = x + sx * r, y + sy * r
            pygame.draw.line(self.surface, (255, 255, 255), (cx, cy), (cx - sx * arm, cy), 2)
            pygame.draw.line(self.surface, (255, 255, 255), (cx, cy), (cx, cy - sy * arm), 2)
        tag = self.font.render(f"#{oid}", True, theme.BG)
        box = tag.get_rect(midbottom=(x, y - r - 2)).inflate(6, 3)
        pygame.draw.rect(self.surface, (255, 255, 255), box, border_radius=3)
        self.surface.blit(tag, tag.get_rect(center=box.center))

    def present(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        # stick the finished plate into the hole the layout left for it
        screen.blit(self.surface, rect.topleft)
        pygame.draw.rect(screen, theme.PANEL_BORDER, rect, width=1, border_radius=6)

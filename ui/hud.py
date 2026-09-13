# the HUD. everything on screen that isnt the plate. does the layout, draws
# the panels and sends mouse events to the right widget. when a button gets
# pressed it calls back into main.py, it doesnt touch the world itself apart
# from reading it for the numbers
#
# header along the top, then a strip with the legend/clock/fps, then the
# plate on the left and a column of text on the right

import random  # not used any more, was for the old sparkline noise
from collections import deque
from typing import Callable, NamedTuple

import pygame

from simulation.ecosystem import Ecosystem
from simulation.genome import TRAIT_NAMES
from simulation.types import Event, Organism
from ui import theme
from ui.charts import draw_trends
from ui.inspector import Descent, Inspector
from ui.widgets import Button, Label, Meter, Slider, draw_panel, hline

HEIGHT = 860  # window height the layout was designed for
WIDTH = 1280


class Replay(NamedTuple):
    # where we are in the recording while replaying
    index: int
    total: int


class Hud:
    def __init__(self, size: tuple[int, int], fonts,
                 on_toggle_pause: Callable[[], None],
                 on_toggle_replay: Callable[[], None],
                 on_seek: Callable[[int], None]) -> None:
        self.fonts = fonts
        self.size = size
        self._on_toggle_pause = on_toggle_pause
        self._on_toggle_replay = on_toggle_replay
        self._on_seek = on_seek
        self._build_layout(size)

        f = fonts
        self.pause_btn = Button((0, 0, 74, 24), "pause", f.body)
        self.replay_btn = Button((0, 0, 74, 24), "replay", f.body, accent=theme.GOLD)
        self.speed_slider = Slider((0, 0, 130, 12), f.small, 0.25, 20.0, 1.0)
        self.mut_slider = Slider((0, 0, 100, 12), f.small, 0.001, 0.20, 0.05,
                                 step=0.001, accent=theme.FOOD)
        # the two world dials, food and the aggression pressure
        self.food_slider = Slider((0, 0, 100, 12), f.small, 0.1, 2.5, 1.0,
                                  step=0.05, accent=theme.FOOD)
        self.pressure_slider = Slider((0, 0, 100, 12), f.small, -1.0, 1.0, 0.0,
                                      step=0.05, accent=theme.PREDATOR, bipolar=True)
        self.scrub = Slider((0, 0, 400, 12), f.small, 0, 239, 0, step=1, accent=theme.GOLD)

        self.clock = Label((0, 0), "0:00", f.small, theme.TEXT_DIM, anchor="midright")
        self.fps = Label((0, 0), "", f.small, theme.TEXT_FAINT, anchor="midright")
        self.state = Label((0, 0), "", f.body, theme.GOLD, anchor="midleft")
        self.replay_pos = Label((0, 0), "", f.small, theme.TEXT, anchor="midright")

        self.env_labels = []
        self._place_header_controls()
        self._place_readouts()

        # the log. (text, colour) pairs. kills go in as they happen because
        # theyre the interesting bit, deaths get added up once a second -
        # a starvation crash would otherwise flood the whole thing
        self.log: deque[tuple[str, tuple[int, int, int]]] = deque(maxlen=40)
        self._pending: dict[str, int] = {}
        self._log_second = -1
        self._last_generation = 1

        # these get recomputed once a second, not every frame
        self._stat_second = -1
        self._averages: dict[str, float] = {}
        self._descent: Descent | None = None

        self.meter = Meter(f.small, label_w=46, value_w=62)

    # where everything goes

    def _build_layout(self, size: tuple[int, int]) -> None:
        w, h = size
        m = theme.MARGIN
        self.header = pygame.Rect(m, m, w - 2 * m, theme.HEADER_H)
        side_x = w - m - theme.SIDEBAR_W
        self.sidebar = pygame.Rect(side_x, self.header.bottom + 8,
                                   theme.SIDEBAR_W, h - self.header.bottom - 8 - m)
        plate_w = side_x - 2 * m
        self.keybar = pygame.Rect(m, self.header.bottom + 8, plate_w, theme.KEYBAR_H)
        self.plate = pygame.Rect(m, self.keybar.bottom + 4, plate_w,
                                 h - self.keybar.bottom - 4 - m)

        # section positions down the sidebar. heights come from the font
        # metrics so nothing overlaps if the fonts change
        f = self.fonts
        pad = theme.PANEL_PAD
        line = f.small.get_height() + 2
        stats_h = pad + f.head.get_height() + 4 + 7 * line + 12
        trends_h = pad + f.head.get_height() + 4 + 96 + line + pad
        log_h = pad + f.head.get_height() + 4 + 6 * line + pad

        y = self.sidebar.top
        self.census_top = y
        y += stats_h
        self.trends_top = y
        y += trends_h
        self.log_top = y
        self.log_bottom = y + log_h
        y += log_h
        self.inspector_top = y + 4
        self.inspector = Inspector(self.fonts)

    def _place_header_controls(self) -> None:
        # laid out from the right edge backwards. world dials first, then a
        # gap, then the sim controls, then the buttons
        f = self.fonts
        cy = self.header.centery
        slider_y = cy - 4
        value_gap, group_gap = 6, 20
        value_w = 44

        def group_width(slider: Slider) -> int:
            return slider.rect.width + value_gap + value_w

        widths = [group_width(s) for s in (self.food_slider, self.pressure_slider,
                                           self.speed_slider, self.mut_slider)]
        total = sum(widths) + group_gap * 3 + 20 + 74 + 8 + 74
        x = self.header.right - 14 - total

        for name, slider, accent in (("food", self.food_slider, theme.FOOD),
                                     ("aggression", self.pressure_slider, theme.PREDATOR)):
            label = Label((x, cy - 11), name, f.small, theme.TEXT_DIM)
            value = Label((x + slider.rect.width + value_gap, cy + 6), "", f.small, accent)
            self.env_labels.append((label, slider, value))
            slider.rect.topleft = (x, slider_y + 8)
            x += group_width(slider) + group_gap

        x += 6
        for name, slider in (("speed", self.speed_slider), ("mutation", self.mut_slider)):
            label = Label((x, cy - 11), name, f.small, theme.TEXT_DIM)
            value = Label((x + slider.rect.width + value_gap, cy + 6), "", f.small, theme.TEXT)
            self.env_labels.append((label, slider, value))
            slider.rect.topleft = (x, slider_y + 8)
            x += group_width(slider) + group_gap

        self.pause_btn.rect.topleft = (x, cy - 12)
        self.replay_btn.rect.topleft = (self.pause_btn.rect.right + 8, cy - 12)

    def _place_readouts(self) -> None:
        self.clock.pos = (self.keybar.right - 4, self.keybar.centery)
        self.fps.pos = (self.keybar.right - 68, self.keybar.centery)
        self.state.pos = (self.plate.left + 10, self.plate.top + 12)

        # the scrub bar sits over the bottom of the plate. geometry is fixed
        # by the layout, not by whether replay is on
        bar = pygame.Rect(self.plate.left, self.plate.bottom - 44, self.plate.width, 36)
        self.scrub.rect = pygame.Rect(bar.left + 80, bar.centery - 6,
                                      bar.width - 80 - 90, 12)

    # slider values

    @property
    def speed(self) -> float:
        return self.speed_slider.value

    @property
    def mutation(self) -> float:
        return self.mut_slider.value

    @property
    def food_scale(self) -> float:
        return self.food_slider.value

    @property
    def pressure(self) -> float:
        return self.pressure_slider.value

    def set_replay_span(self, total: int) -> None:
        self.scrub.max = max(1, total - 1)
        self.scrub.value = 0

    def widgets(self) -> tuple:
        return (self.pause_btn, self.replay_btn, self.speed_slider, self.mut_slider,
                self.food_slider, self.pressure_slider, self.scrub)

    def chrome_at(self, pos: tuple[int, int], replaying: bool) -> bool:
        # is this point on the ui rather than the plate. otherwise clicking a
        # panel would also select whatever creature is underneath it
        if self.header.collidepoint(pos) or self.keybar.collidepoint(pos):
            return True
        if self.sidebar.collidepoint(pos):
            return True
        if replaying and self.scrub.track.collidepoint(pos):
            return True
        return any(w.rect.collidepoint(pos) for w in self.widgets())

    # mouse and keyboard

    def handle(self, event: pygame.event.Event, replaying: bool) -> None:
        if self.pause_btn.handle(event):
            self._on_toggle_pause()
        if self.replay_btn.handle(event):
            self._on_toggle_replay()
        self.speed_slider.handle(event)
        self.mut_slider.handle(event)
        self.food_slider.handle(event)
        self.pressure_slider.handle(event)
        if replaying:
            self.scrub.handle(event)
            if self.scrub.dragging:
                self._on_seek(int(self.scrub.value))

    # the log

    def consume(self, events: list[Event], world_time: float,
                max_generation: int) -> None:
        for e in events:
            if e.kind == "eaten":
                self.log.append((f"#{e.actor} eaten by #{e.other}", theme.PREDATOR))
            elif e.kind in ("starved", "aged", "arrived"):
                self._pending[e.kind] = self._pending.get(e.kind, 0) + 1

        second = int(world_time)
        if second != self._log_second:
            self._log_second = second
            parts = [f"{n} {kind}" for kind, n in self._pending.items() if n]
            self._pending.clear()
            if parts:
                stamp = f"{second // 60}:{second % 60:02d}"
                self.log.append((f"{stamp}  " + ", ".join(parts), theme.TEXT_FAINT))
        if max_generation > self._last_generation:
            self._last_generation = max_generation
            self.log.append((f"generation {max_generation}", theme.ACCENT))

    # a few numbers only need updating once a second

    def _refresh(self, world: Ecosystem, selected: Organism | None) -> None:
        second = int(world.time)
        if second == self._stat_second:
            return
        self._stat_second = second
        self._averages = {name: world.trait_average(name) for name in TRAIT_NAMES}
        if selected is None:
            self._descent = None
            return
        self._descent = Descent(
            line=len(world.lineage_members(selected.lineage)),
            descendants=len(world.descendants_of(selected.id)),
            population=len(world.organisms),
        )

    # drawing

    def draw(self, screen: pygame.Surface, world: Ecosystem, selected: Organism | None,
             kin: frozenset[int], paused: bool, replay: Replay | None,
             fps: float, mouse: tuple[int, int]) -> None:
        self._refresh(world, selected)
        self._draw_header(screen, paused, replay is not None, mouse)
        self._draw_keybar(screen, world, paused, replay, fps)
        self._draw_stats(screen, world)
        self._draw_trends(screen, world)
        self._draw_log(screen)
        self.inspector.draw(screen, self.sidebar, self.inspector_top,
                            self.sidebar.bottom, selected, world.config,
                            self._averages, self._descent)
        if replay is not None:
            self._draw_scrub(screen, replay, mouse)
        else:
            self._draw_hints(screen)

    def _draw_header(self, screen: pygame.Surface, paused: bool,
                     replaying: bool, mouse: tuple[int, int]) -> None:
        draw_panel(screen, self.header)
        f = self.fonts
        logo = f.logo.render("EVOLAB", True, theme.ACCENT)
        screen.blit(logo, (self.header.left + 14, self.header.centery - logo.get_height() // 2))

        self.pause_btn.label = "resume" if paused else "pause"
        self.pause_btn.active = paused
        self.pause_btn.draw(screen, mouse)
        self.replay_btn.label = "live" if replaying else "replay"
        self.replay_btn.active = replaying
        self.replay_btn.draw(screen, mouse)

        # the four sliders, each with its name above and value below
        values = (f"{self.food_scale:.2f}x",
                  f"{self.pressure:+.2f}",
                  f"{self.speed:.2f}x",
                  f"{self.mutation * 100:.1f}%")
        for (label, slider, value), text in zip(self.env_labels, values):
            label.draw(screen)
            slider.draw(screen, mouse)
            value.set_text(text)
            value.draw(screen)

    def _draw_keybar(self, screen: pygame.Surface, world: Ecosystem, paused: bool,
                     replay: Replay | None, fps: float) -> None:
        # one line of text under the header saying what the colours mean
        f = self.fonts
        y = self.keybar.centery
        text = "green eats plants    red hunts    amber is food    white ring = ready to breed"
        screen.blit(f.small.render(text, True, theme.TEXT_FAINT), (self.keybar.left + 2, y - 7))

        self.fps.set_text(f"{fps:.0f} fps")
        self.fps.draw(screen)
        seconds = int(world.time)
        self.clock.set_text(f"{seconds // 60}:{seconds % 60:02d}")
        self.clock.draw(screen)

        if paused or replay is not None:
            self.state.set_text("replay" if replay is not None else "paused")
            self.state.draw(screen)

    def _row(self, screen: pygame.Surface, x: int, y: int, width: int,
             label: str, value: str, color=theme.TEXT) -> None:
        # label on the left, value on the right. cheaper than tiles
        f = self.fonts
        screen.blit(f.small.render(label, True, theme.TEXT_DIM), (x, y))
        rendered = f.small.render(value, True, color)
        screen.blit(rendered, (x + width - rendered.get_width(), y))

    def _draw_stats(self, screen: pygame.Surface, world: Ecosystem) -> None:
        f = self.fonts
        pad = theme.PANEL_PAD
        x = self.sidebar.left + pad
        width = self.sidebar.width - 2 * pad
        y = self.census_top + pad
        screen.blit(f.head.render("stats", True, theme.TEXT), (x, y))
        y += f.head.get_height() + 4

        deaths = world.deaths
        for label, value, color in (
            ("population", str(len(world.organisms)), theme.ACCENT),
            ("food", str(len(world.food)), theme.FOOD),
            ("generation", str(world.max_generation), theme.TEXT),
            ("births", str(world.births), theme.TEXT),
            ("starved", str(deaths["starvation"]), theme.TEXT_DIM),
            ("eaten", str(deaths["eaten"]), theme.PREDATOR),
        ):
            self._row(screen, x, y, width, label, value, color)
            y += f.small.get_height() + 2

        prey, mixed, pred = world.role_counts()
        y += 6
        self._row(screen, x, y, width, "prey / mixed / hunters",
                  f"{prey} / {mixed} / {pred}")
        hline(screen, x, y + f.small.get_height() + 4, width)

    def _draw_trends(self, screen: pygame.Surface, world: Ecosystem) -> None:
        f = self.fonts
        pad = theme.PANEL_PAD
        x = self.sidebar.left + pad
        width = self.sidebar.width - 2 * pad
        y = self.trends_top + pad
        screen.blit(f.head.render("last 5 minutes", True, theme.TEXT), (x, y))
        y += f.head.get_height() + 4
        chart = pygame.Rect(x, y, width, 96)
        draw_trends(screen, chart, world.history, f, world.config)

    def _draw_log(self, screen: pygame.Surface) -> None:
        f = self.fonts
        pad = theme.PANEL_PAD
        x = self.sidebar.left + pad
        width = self.sidebar.width - 2 * pad
        y = self.log_top + pad
        screen.blit(f.head.render("recent", True, theme.TEXT), (x, y))
        y += f.head.get_height() + 4
        line = f.small.get_height() + 2
        room = max(0, (self.log_bottom - pad - y) // line)
        for text, color in list(self.log)[-room:][::-1]:
            screen.blit(f.small.render(text, True, color), (x, y))
            y += line
        hline(screen, x, self.inspector_top - 4, width)

    def _draw_scrub(self, screen: pygame.Surface, replay: Replay,
                    mouse: tuple[int, int]) -> None:
        # the replay bar, sits over the bottom of the plate
        bar = pygame.Rect(self.plate.left, self.plate.bottom - 44, self.plate.width, 36)
        pygame.draw.rect(screen, theme.PANEL, bar)
        pygame.draw.rect(screen, theme.GOLD, bar, width=1)
        f = self.fonts
        screen.blit(f.small.render("replay", True, theme.GOLD), (bar.left + 10, bar.centery - 7))
        self.scrub.draw(screen, mouse)
        self.replay_pos.pos = (bar.right - 10, bar.centery)
        self.replay_pos.set_text(f"{replay.index + 1} / {replay.total}")
        self.replay_pos.draw(screen)

    def _draw_hints(self, screen: pygame.Surface) -> None:
        # plain text in the corner of the plate, no boxes
        f = self.fonts
        text = "space pause,  r replay,  click a creature"
        surface = f.small.render(text, True, theme.TEXT_FAINT)
        screen.blit(surface, (self.plate.left + 10,
                              self.plate.bottom - surface.get_height() - 8))

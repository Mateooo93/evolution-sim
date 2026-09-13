# the HUD. everything on screen that isnt the actual plate.
# it does the layout, draws the panels and routes the mouse to the right
# widget. when a button gets pressed it calls back into main.py, it doesnt
# touch the world itself (apart from reading it to draw the numbers)
#
# layout is header on top, then a legend bar with the clock, then the plate
# on the left and the sidebar panels stacked down the right hand side
import random  # not used any more, was for the old sparkline noise
from collections import deque
from typing import Callable, NamedTuple

import pygame

from simulation.ecosystem import Ecosystem
from simulation.genome import TRAIT_NAMES, role_of
from simulation.types import Event, Organism
from ui import theme
from ui.charts import draw_trends
from ui.inspector import Descent, Inspector
from ui.widgets import (
    Button,
    Label,
    Meter,
    Slider,
    draw_panel,
    draw_tile,
    keycap,
    stat_tile,
)

HEIGHT = 860  # window height the layout is designed for
WIDTH = 1280

TILE_ROWS = 2
TILE_COLS = 3


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

        # the widgets in the header
        f = fonts
        self.pause_btn = Button((0, 0, 78, 30), "Pause", f.button)
        self.replay_btn = Button((0, 0, 78, 30), "Replay", f.button, accent=theme.GOLD)
        self.speed_slider = Slider((0, 0, 150, 16), f.small, 0.25, 20.0, 1.0)
        self.mut_slider = Slider((0, 0, 110, 16), f.small, 0.001, 0.20, 0.05,
                                 step=0.001, accent=theme.FOOD)
        # The two environment dials: the world's food supply and the
        # selection regime the lab imposes on aggression.
        self.food_slider = Slider((0, 0, 110, 16), f.small, 0.1, 2.5, 1.0,
                                  step=0.05, accent=theme.FOOD)
        self.pressure_slider = Slider((0, 0, 110, 16), f.small, -1.0, 1.0, 0.0,
                                      step=0.05, accent=theme.PREDATOR, bipolar=True)
        # Time-machine scrub bar (only drawn while replaying).
        self.scrub = Slider((0, 0, 400, 14), f.small, 0, 239, 0, step=1, accent=theme.GOLD)

        self.clock = Label((0, 0), "T+ 0:00", f.small, theme.TEXT_DIM, anchor="midright")
        self.fps = Label((0, 0), "60 fps", f.small, theme.TEXT_FAINT, anchor="midright")
        self.state = Label((0, 0), "", f.title, theme.GOLD, anchor="midleft")
        self.replay_pos = Label((0, 0), "", f.small, theme.TEXT, anchor="midright")
        self._place_header_controls()
        self._place_readouts()

        # the RECENT log
        # (text, colour) pairs. kills go in the second they happen because
        # theyre the interesting bit, but deaths get summed up once per
        # second - a starvation crash would otherwise flood the whole panel
        self.log: deque[tuple[str, tuple[int, int, int]]] = deque(maxlen=40)
        self._pending: dict[str, int] = {}
        self._log_second = -1
        self._last_generation = 1

        # these get recomputed once a second, not every frame. looping the
        # population 60x a second for the trait averages was silly
        self._stat_second = -1
        self._averages: dict[str, float] = {}
        self._descent: Descent | None = None

        self.meter = Meter(f.small, label_w=44, value_w=0)  # value_w 0 = no numbers

    # working out where everything goes

    def _build_layout(self, size: tuple[int, int]) -> None:
        # work out where everything goes. panel heights come from the font
        # metrics so nothing overlaps if the fonts change
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

        # the sidebar, top to bottom
        f = self.fonts
        pad = theme.PANEL_PAD
        tile_h = f.metric.get_height() + f.small.get_height() + 6
        census_h = (2 * pad + f.title.get_height() + 6
                    + TILE_ROWS * tile_h + (TILE_ROWS - 1) * 6
                    + 8 + f.small.get_height() + 12)
        trends_h = 2 * pad + f.title.get_height() + 6 + 100 + f.small.get_height() + 2
        log_h = 2 * pad + f.title.get_height() + 6 + 6 * (f.small.get_height() + 2)

        y = self.sidebar.top
        self.census_panel = pygame.Rect(self.sidebar.left, y, self.sidebar.width, census_h)
        y = self.census_panel.bottom + theme.GAP
        self.trends_panel = pygame.Rect(self.sidebar.left, y, self.sidebar.width, trends_h)
        y = self.trends_panel.bottom + theme.GAP
        self.log_panel = pygame.Rect(self.sidebar.left, y, self.sidebar.width, log_h)
        y = self.log_panel.bottom + theme.GAP
        self.inspector_panel = pygame.Rect(self.sidebar.left, y, self.sidebar.width,
                                           self.sidebar.bottom - y)
        self.inspector = Inspector(self.fonts)

    def _place_header_controls(self) -> None:
        # lay the toolbar out from the right edge backwards. two groups:
        # the world dials (food, aggression) then a divider then the sim
        # controls (speed, mutation) then the buttons. the divider is there
        # so it reads as two different kinds of control
        f = self.fonts
        cy = self.header.centery
        slider_y = cy - 6
        value_gap, group_gap = 8, 18
        value_w = 46
        divider_gap = 13

        def group_width(slider: Slider) -> int:
            return slider.rect.width + value_gap + value_w

        widths = [group_width(s) for s in
                  (self.food_slider, self.pressure_slider, self.speed_slider,
                   self.mut_slider)]
        total = (sum(widths) + group_gap * 3 + 2 * divider_gap
                 + 78 + 8 + 78)
        x = self.header.right - 16 - total

        self.env_labels = []
        for label_text, slider, value_text, color in (
            ("FOOD", self.food_slider, "1.00×", theme.FOOD),
            ("AGGRESSION", self.pressure_slider, "0.00", theme.PREDATOR),
        ):
            self.env_labels.append(
                (Label((x, cy - 14), label_text, f.tiny, theme.TEXT_FAINT), slider,
                 Label((x + slider.rect.width + value_gap, cy), value_text, f.small, color))
            )
            slider.rect.topleft = (x, slider_y)
            x += group_width(slider) + group_gap

        self.divider_x = x - group_gap + divider_gap // 2
        x += 2 * divider_gap - group_gap

        self.speed_label = Label((x, cy - 14), "SPEED", f.tiny, theme.TEXT_FAINT)
        self.speed_slider.rect.topleft = (x, slider_y)
        self.speed_value = Label((x + self.speed_slider.rect.width + value_gap, cy),
                                 "1.0x", f.small, theme.TEXT)
        x += group_width(self.speed_slider) + group_gap

        self.mut_label = Label((x, cy - 14), "MUTATION", f.tiny, theme.TEXT_FAINT)
        self.mut_slider.rect.topleft = (x, slider_y)
        self.mut_value = Label((x + self.mut_slider.rect.width + value_gap, cy),
                               "5.0%", f.small, theme.TEXT)
        x += group_width(self.mut_slider) + group_gap

        self.pause_btn.rect.topleft = (x, cy - 15)
        self.replay_btn.rect.topleft = (self.pause_btn.rect.right + 8, cy - 15)

    def _place_readouts(self) -> None:
        # the clock/fps in the legend bar and the replay scrub bar
        self.clock.pos = (self.keybar.right - 8 - 74, self.keybar.centery)
        self.fps.pos = (self.keybar.right - 8, self.keybar.centery)
        self.state.pos = (self.plate.left + 12, self.plate.top + 14)

        # The scrub bar sits over the foot of the plate; its geometry is
        # fixed by the layout, not by whether replay is currently on.
        bar = pygame.Rect(self.plate.left, self.plate.bottom - 46, self.plate.width, 40)
        pos_w = 78
        self.scrub.rect = pygame.Rect(bar.left + 92, bar.centery - 7,
                                      bar.width - 92 - pos_w - 16, 14)

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

    # how long the recording is, so the scrub bar covers exactly it
    def set_replay_span(self, total: int) -> None:
        self.scrub.max = max(1, total - 1)
        self.scrub.value = 0

    def widgets(self) -> tuple:
        return (self.pause_btn, self.replay_btn, self.speed_slider, self.mut_slider,
                self.food_slider, self.pressure_slider, self.scrub)

    def chrome_at(self, pos: tuple[int, int], replaying: bool) -> bool:
        # is this point on the UI rather than the plate. otherwise clicking
        # a panel would also try to select whatever creature is underneath
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
                self.log.append((f"{stamp}  " + " · ".join(parts), theme.TEXT_FAINT))
        if max_generation > self._last_generation:
            self._last_generation = max_generation
            self.log.append((f"generation {max_generation} reached", theme.ACCENT))

    # numbers that only need updating once a second

    def _refresh(self, world: Ecosystem, selected: Organism | None) -> None:
        # once a second: population averages + the selected ones family
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

    # panels

    def draw(self, screen: pygame.Surface, world: Ecosystem, selected: Organism | None,
             kin: frozenset[int], paused: bool, replay: Replay | None,
             fps: float, mouse: tuple[int, int]) -> None:
        self._refresh(world, selected)
        self._draw_header(screen, paused, replay is not None, mouse)
        self._draw_keybar(screen, world, paused, replay, fps)
        self._draw_census(screen, world)
        self._draw_trends(screen, world)
        self._draw_log(screen)
        self.inspector.draw(screen, self.inspector_panel, selected, world.config,
                            self._averages, self._descent)
        if replay is not None:
            self._draw_scrub(screen, replay, mouse)
        else:
            self._draw_hints(screen)

    def _draw_header(self, screen: pygame.Surface, paused: bool,
                     replaying: bool, mouse: tuple[int, int]) -> None:
        draw_panel(screen, self.header)
        f = self.fonts
        x = self.header.left + 16
        logo = f.logo.render("EVOLAB", True, theme.ACCENT)
        screen.blit(logo, (x, self.header.top + 8))
        tag = f.tagline.render("artificial life, running live", True, theme.TEXT_FAINT)
        screen.blit(tag, (x, self.header.top + 8 + logo.get_height() + 1))

        self.pause_btn.label = "Resume" if paused else "Pause"
        self.pause_btn.active = paused
        self.pause_btn.draw(screen, mouse)
        self.replay_btn.label = "Live" if replaying else "Replay"
        self.replay_btn.active = replaying
        self.replay_btn.draw(screen, mouse)

        # Environment dials, then the hairline, then the sim controls.
        for (label, slider, value), text in zip(
            self.env_labels,
            (f"{self.food_scale:.2f}×",
             f"{self.pressure:+.2f}" if self.pressure else "0.00"),
        ):
            label.draw(screen)
            slider.draw(screen, mouse)
            if value.text != text:
                value.set_text(text)
            value.draw(screen)
        pygame.draw.line(
            screen, theme.PANEL_BORDER,
            (self.divider_x, self.header.top + 12),
            (self.divider_x, self.header.bottom - 12), 1,
        )

        self.speed_label.draw(screen)
        self.speed_slider.draw(screen, mouse)
        self.speed_value.set_text(f"{self.speed_slider.value:.2f}x")
        self.speed_value.draw(screen)
        self.mut_label.draw(screen)
        self.mut_slider.draw(screen, mouse)
        self.mut_value.set_text(f"{self.mut_slider.value * 100:.1f}%")
        self.mut_value.draw(screen)

    def _draw_keybar(self, screen: pygame.Surface, world: Ecosystem, paused: bool,
                     replay: Replay | None, fps: float) -> None:
        # the strip under the header: what all the colours mean + clock + fps
        draw_panel(screen, self.keybar, radius=6)
        f = self.fonts
        x = self.keybar.left + 10
        y = self.keybar.centery
        items = (
            (theme.ACCENT, "prey — forages plants", False),
            (theme.PREDATOR, "predator — hunts prey", False),
            (theme.FOOD, "food", False),
            (theme.TEXT, "ready to mate", True),
            (theme.ACCENT_DIM, "family line", True),
        )
        for color, text, hollow in items:
            pygame.draw.circle(screen, color, (x + 3, y), 4 if hollow else 3,
                               1 if hollow else 0)
            label = f.small.render(text, True, theme.TEXT_FAINT)
            screen.blit(label, label.get_rect(midleft=(x + 10, y)))
            x += 10 + label.get_width() + 14

        self.fps.set_text(f"{fps:.0f} fps")
        self.fps.draw(screen)
        seconds = int(world.time)
        self.clock.set_text(f"T+ {seconds // 60}:{seconds % 60:02d}")
        self.clock.draw(screen)

        self.state.set_text(
            "REPLAYING" if replay is not None else ("PAUSED" if paused else "")
        )
        if self.state.text:
            self.state.draw(screen)

    def _draw_census(self, screen: pygame.Surface, world: Ecosystem) -> None:
        # population / food / generation / births / starved / eaten tiles
        draw_panel(screen, self.census_panel)
        f = self.fonts
        pad = theme.PANEL_PAD
        x0 = self.census_panel.left + pad
        y = self.census_panel.top + pad
        screen.blit(f.title.render("ECOSYSTEM", True, theme.TEXT_DIM), (x0, y))
        y += f.title.get_height() + 6

        deaths = world.deaths
        tiles = (
            (str(len(world.organisms)), "population", theme.ACCENT),
            (str(len(world.food)), "food", theme.FOOD),
            (str(world.max_generation), "generation", theme.TEXT),
            (str(world.births), "births", theme.TEXT),
            (str(deaths["starvation"]), "starved", theme.TEXT_FAINT),
            (str(deaths["eaten"]), "eaten", theme.PREDATOR),
        )
        tile_h = f.metric.get_height() + f.small.get_height() + 6
        gap = 6
        tile_w = (self.census_panel.width - 2 * pad - (TILE_COLS - 1) * gap) // TILE_COLS
        for i, (value, caption, color) in enumerate(tiles):
            row, col = divmod(i, TILE_COLS)
            rect = pygame.Rect(x0 + col * (tile_w + gap), y + row * (tile_h + gap),
                               tile_w, tile_h)
            stat_tile(screen, rect, value, caption, f, color)
        y += TILE_ROWS * tile_h + (TILE_ROWS - 1) * gap + 10

        # the diet bar. prey green, mixed amber, predators red
        prey, mixed, pred = world.role_counts()
        total = max(1, prey + mixed + pred)
        bar = pygame.Rect(x0, y + f.small.get_height() + 2,
                          self.census_panel.width - 2 * pad, 8)
        pygame.draw.rect(screen, theme.METER_BG, bar, border_radius=4)
        x = bar.left
        for count, color in ((prey, theme.ACCENT), (mixed, theme.FOOD), (pred, theme.PREDATOR)):
            width = round(bar.width * count / total)
            if width:
                pygame.draw.rect(screen, color, (x, bar.top, width, bar.height))
            x += width
        screen.blit(
            f.small.render(
                f"{prey} prey · {mixed} mixed · {pred} predators", True, theme.TEXT_DIM),
            (x0, y),
        )

    def _draw_trends(self, screen: pygame.Surface, world: Ecosystem) -> None:
        draw_panel(screen, self.trends_panel)
        f = self.fonts
        pad = theme.PANEL_PAD
        x0 = self.trends_panel.left + pad
        y = self.trends_panel.top + pad
        screen.blit(f.title.render("TRENDS  ·  last 5 min", True, theme.TEXT_DIM), (x0, y))
        y += f.title.get_height() + 6
        draw_trends(
            screen,
            pygame.Rect(x0, y, self.trends_panel.width - 2 * pad,
                        self.trends_panel.bottom - pad - y),
            world.history, f, world.config,
        )

    def _draw_log(self, screen: pygame.Surface) -> None:
        # newest line at the top, however many fit in the panel
        draw_panel(screen, self.log_panel)
        f = self.fonts
        pad = theme.PANEL_PAD
        x0 = self.log_panel.left + pad
        y = self.log_panel.top + pad
        screen.blit(f.title.render("RECENT", True, theme.TEXT_DIM), (x0, y))
        y += f.title.get_height() + 6
        line_h = f.small.get_height() + 2
        room = max(0, (self.log_panel.bottom - pad - y) // line_h)
        for text, color in list(self.log)[-room:][::-1]:
            screen.blit(f.small.render(text, True, color), (x0, y))
            y += line_h

    def _draw_scrub(self, screen: pygame.Surface, replay: Replay,
                    mouse: tuple[int, int]) -> None:
        # the replay bar. it sits over the bottom of the plate like a video
        # player timeline. TODO clicking the plate under it is blocked while
        # replaying, which is fine for now
        bar = pygame.Rect(self.plate.left, self.plate.bottom - 46, self.plate.width, 40)
        pygame.draw.rect(screen, theme.PANEL, bar, border_radius=6)
        pygame.draw.rect(screen, theme.GOLD, bar, width=1, border_radius=6)

        f = self.fonts
        pygame.draw.circle(screen, theme.GOLD, (bar.left + 18, bar.centery), 4)
        tag = f.title.render("REPLAY", True, theme.GOLD)
        screen.blit(tag, tag.get_rect(midleft=(bar.left + 28, bar.centery)))

        self.scrub.draw(screen, mouse)
        self.replay_pos.pos = (bar.right - 12, bar.centery)
        self.replay_pos.set_text(f"{replay.index + 1} / {replay.total}")
        self.replay_pos.draw(screen)

    def _draw_hints(self, screen: pygame.Surface) -> None:
        # little key hints in the corner of the plate
        f = self.fonts
        hints = (("SPACE", "pause"), ("R", "replay"), ("click", "inspect a creature"))
        width = sum(
            f.keycap.size(key)[0] + 8 + 5 + f.small.size(text)[0] + 16
            for key, text in hints
        )
        panel = pygame.Rect(self.plate.left + 8,
                            self.plate.bottom - 8 - f.small.get_height() - 14,
                            width + 4, f.small.get_height() + 14)
        pygame.draw.rect(screen, theme.PANEL, panel, border_radius=6)
        pygame.draw.rect(screen, theme.PANEL_BORDER, panel, width=1, border_radius=6)
        x = panel.left + 8
        for key, text in hints:
            x += keycap(screen, (x, panel.centery), key, f, text) + 16

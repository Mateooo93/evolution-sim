"""Hand-drawn UI widgets.

pygame ships no controls, so every element here is drawn from primitives.
Each widget owns its rect, draws itself from palette values, and returns
True from `handle` when it was activated. Widgets are stateless apart
from hover/press flags — the app keeps the real state — so a panel can be
redrawn at any time from the current world.

`draw` takes the current mouse position so hover states are available
without widgets reaching for global state themselves.
"""

import pygame

from ui import theme


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, radius: int = 8) -> None:
    """The standard chrome surface: a raised panel with a hairline border."""
    pygame.draw.rect(surface, theme.PANEL, rect, border_radius=radius)
    pygame.draw.rect(surface, theme.PANEL_BORDER, rect, width=1, border_radius=radius)


def draw_tile(surface: pygame.Surface, rect: pygame.Rect, hover: bool = False,
              color: tuple[int, int, int] = theme.RAISED) -> None:
    pygame.draw.rect(surface, theme.RAISED_HOVER if hover else color, rect, border_radius=6)


class Label:
    """A single line of text, re-rendered only when it changes."""

    def __init__(
        self,
        pos: tuple[int, int],
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int] = theme.TEXT,
        anchor: str = "midleft",
    ) -> None:
        self.pos = pos
        self.font = font
        self.color = color
        self.anchor = anchor  # any pygame.Rect anchor name
        self.text = text
        self.surface = font.render(text, True, color)

    def set_text(self, text: str) -> None:
        if text != self.text:
            self.text = text
            self.surface = self.font.render(text, True, self.color)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.surface, self.surface.get_rect(**{self.anchor: self.pos}))


class Button:
    """A clickable label. `active` inverts it (used for Pause / Replay)."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        label: str,
        font: pygame.font.Font,
        active: bool = False,
        accent: tuple[int, int, int] = theme.ACCENT,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.active = active
        self.accent = accent
        self._pressed = False

    def handle(self, event: pygame.event.Event) -> bool:
        """Process one event; True when the button was clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            clicked = self._pressed and self.rect.collidepoint(event.pos)
            self._pressed = False
            return clicked
        return False

    def draw(self, surface: pygame.Surface, mouse: tuple[int, int] = (0, 0)) -> None:
        hovered = self.rect.collidepoint(mouse)
        fill = self.accent if self.active else (
            theme.RAISED_HOVER if hovered else theme.RAISED
        )
        border = self.accent if (self.active or hovered) else theme.PANEL_BORDER
        text_color = theme.BG if self.active else theme.TEXT
        pygame.draw.rect(surface, fill, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, width=1, border_radius=6)
        text = self.font.render(self.label, True, text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))


class Slider:
    """Horizontal slider with a filled track; value snapped to `step`."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        font: pygame.font.Font,
        min_value: float,
        max_value: float,
        value: float,
        step: float = 0.25,
        accent: tuple[int, int, int] = theme.ACCENT,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.font = font
        self.min = min_value
        self.max = max_value
        self.step = step
        self.accent = accent
        self._value = value
        self._drag = False

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        v = max(self.min, min(self.max, v))
        self._value = round(v / self.step) * self.step

    @property
    def dragging(self) -> bool:
        """True while the user holds the knob (pauses timed auto-advance)."""
        return self._drag

    @property
    def track(self) -> pygame.Rect:
        """The clickable band, taller than the drawn line so it is easy to hit."""
        return self.rect.inflate(0, 12)

    def _set_from_x(self, x: int) -> None:
        t = max(0.0, min(1.0, (x - self.rect.left) / max(1, self.rect.width)))
        self._value = round((self.min + t * (self.max - self.min)) / self.step) * self.step

    def _knob_x(self) -> int:
        t = (self._value - self.min) / (self.max - self.min)
        return self.rect.left + round(t * self.rect.width)

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._drag = self.track.collidepoint(event.pos)
            if self._drag:
                self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self._drag:
            self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = False

    def draw(self, surface: pygame.Surface, mouse: tuple[int, int] = (0, 0)) -> None:
        y = self.rect.centery
        hovered = self.track.collidepoint(mouse) or self._drag
        pygame.draw.line(surface, theme.METER_BG, (self.rect.left, y), (self.rect.right, y), 4)
        knob = self._knob_x()
        if knob > self.rect.left:
            pygame.draw.line(surface, self.accent, (self.rect.left, y), (knob, y), 4)
        if hovered:
            pygame.draw.circle(surface, theme.ACCENT_DIM, (knob, y), 9)
        pygame.draw.circle(surface, self.accent, (knob, y), 6)
        pygame.draw.circle(surface, theme.BG, (knob, y), 2)


class Meter:
    """A labelled progress bar: `label  ▓▓▓░░░  62/100`."""

    def __init__(self, font: pygame.font.Font, label_w: int = 34, value_w: int = 62) -> None:
        self.font = font
        self.label_w = label_w
        self.value_w = value_w

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        fraction: float,
        text: str,
        color: tuple[int, int, int] = theme.ACCENT,
    ) -> None:
        surface.blit(self.font.render(label, True, theme.TEXT_DIM), (rect.left, rect.top))
        bar = pygame.Rect(
            rect.left + self.label_w, rect.top + 1,
            max(8, rect.width - self.label_w - self.value_w), 8,
        )
        pygame.draw.rect(surface, theme.METER_BG, bar, border_radius=4)
        frac = max(0.0, min(1.0, fraction))
        if frac > 0.0:
            filled = pygame.Rect(bar.left, bar.top, max(2, round(bar.width * frac)), bar.height)
            pygame.draw.rect(surface, color, filled, border_radius=4)
        surface.blit(
            self.font.render(text, True, theme.TEXT),
            (bar.right + 6, rect.top),
        )


def stat_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    value: str,
    caption: str,
    fonts,
    color: tuple[int, int, int] = theme.TEXT,
) -> None:
    """A number with a caption under it — the census readout unit."""
    draw_tile(surface, rect)
    big = fonts.metric.render(value, True, color)
    surface.blit(big, big.get_rect(midtop=(rect.centerx, rect.top + 4)))
    cap = fonts.small.render(caption, True, theme.TEXT_FAINT)
    surface.blit(cap, cap.get_rect(midbottom=(rect.centerx, rect.bottom - 4)))


def keycap(surface: pygame.Surface, pos: tuple[int, int], key: str, fonts,
           text: str) -> int:
    """Draw `[key] hint` with the key in a little box; return the width used."""
    rendered = fonts.keycap.render(key, True, theme.TEXT_DIM)
    box = pygame.Rect(pos[0], pos[1] - 7, rendered.get_width() + 8, 14)
    pygame.draw.rect(surface, theme.RAISED, box, border_radius=3)
    pygame.draw.rect(surface, theme.PANEL_BORDER, box, width=1, border_radius=3)
    surface.blit(rendered, rendered.get_rect(center=box.center))
    hint = fonts.small.render(text, True, theme.TEXT_FAINT)
    surface.blit(hint, hint.get_rect(midleft=(box.right + 5, pos[1])))
    return box.width + 5 + hint.get_width()

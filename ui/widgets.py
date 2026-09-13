# the ui widgets. pygame has no buttons or sliders so these are drawn out of
# rectangles. i deliberately kept them plain - no rounded corners, no fills,
# nothing that looks like a template

import pygame

from ui import theme


def draw_panel(surface: pygame.Surface, rect: pygame.Rect) -> None:
    # a flat box with a 1px border. used for the header and the sidebar
    pygame.draw.rect(surface, theme.PANEL, rect)
    pygame.draw.rect(surface, theme.PANEL_BORDER, rect, width=1)


def hline(surface: pygame.Surface, x: int, y: int, width: int) -> None:
    # the separator between sidebar sections
    pygame.draw.line(surface, theme.PANEL_BORDER, (x, y), (x + width, y), 1)


class Label:
    # a bit of text. only re-renders when the string actually changes
    def __init__(self, pos, text, font, color=theme.TEXT, anchor="midleft") -> None:
        self.pos = pos
        self.font = font
        self.color = color
        self.anchor = anchor
        self.text = text
        self.surface = font.render(text, True, color)

    def set_text(self, text: str) -> None:
        if text != self.text:
            self.text = text
            self.surface = self.font.render(text, True, self.color)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.surface, self.surface.get_rect(**{self.anchor: self.pos}))


class Button:
    # text in a box. active just means the text goes accent coloured
    def __init__(self, rect, label, font, active=False, accent=theme.ACCENT) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.active = active
        self.accent = accent
        self._pressed = False

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            clicked = self._pressed and self.rect.collidepoint(event.pos)
            self._pressed = False
            return clicked
        return False

    def draw(self, surface: pygame.Surface, mouse: tuple[int, int] = (0, 0)) -> None:
        hovered = self.rect.collidepoint(mouse)
        color = self.accent if (self.active or hovered) else theme.TEXT_DIM
        pygame.draw.rect(surface, theme.PANEL_BORDER, self.rect, width=1)
        text = self.font.render(self.label, True, color)
        surface.blit(text, text.get_rect(center=self.rect.center))


class Slider:
    # a line with a knob on it. value snaps to step
    def __init__(self, rect, font, min_value, max_value, value, step=0.25,
                 accent=theme.ACCENT, bipolar=False) -> None:
        self.rect = pygame.Rect(rect)
        self.font = font
        self.min = min_value
        self.max = max_value
        self.step = step
        self.accent = accent
        # bipolar ones (-1..1) fill out from the middle so 0 looks empty
        self.bipolar = bipolar
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
        return self._drag

    @property
    def track(self) -> pygame.Rect:
        # the drawn line is thin, the clickable bit is not
        return self.rect.inflate(0, 12)

    def _set_from_x(self, x: int) -> None:
        t = max(0.0, min(1.0, (x - self.rect.left) / max(1, self.rect.width)))
        self._value = round((self.min + t * (self.max - self.min)) / self.step) * self.step

    def _knob_x(self) -> int:
        t = (self._value - self.min) / (self.max - self.min)
        return self.rect.left + round(t * self.rect.width)

    def _origin_x(self) -> int:
        return (self.rect.left + self.rect.width // 2) if self.bipolar else self.rect.left

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
        pygame.draw.line(surface, theme.METER_BG, (self.rect.left, y), (self.rect.right, y), 2)
        knob = self._knob_x()
        origin = self._origin_x()
        if knob != origin:
            lo, hi = min(knob, origin), max(knob, origin)
            pygame.draw.line(surface, self.accent, (lo, y), (hi, y), 2)
        # square knob, it was a circle with a glow on it for a while and it
        # looked like a phone settings screen
        pygame.draw.rect(surface, self.accent, (knob - 3, y - 6, 6, 12))


class Meter:
    # label, bar, value. energy / age / readiness in the inspector
    def __init__(self, font, label_w=44, value_w=64) -> None:
        self.font = font
        self.label_w = label_w
        self.value_w = value_w

    def draw(self, surface, rect, label, fraction, text, color=theme.ACCENT) -> None:
        surface.blit(self.font.render(label, True, theme.TEXT_DIM), (rect.left, rect.top))
        bar = pygame.Rect(rect.left + self.label_w, rect.top + 3,
                          max(8, rect.width - self.label_w - self.value_w), 7)
        pygame.draw.rect(surface, theme.METER_BG, bar)
        frac = max(0.0, min(1.0, fraction))
        if frac > 0.0:
            pygame.draw.rect(surface, color,
                             (bar.left, bar.top, max(2, round(bar.width * frac)), bar.height))
        surface.blit(self.font.render(text, True, theme.TEXT), (bar.right + 6, rect.top))

"""Tiny hand-drawn UI widgets (pygame draws its own control elements).

These are the building blocks for every panel later: controls sidebar,
organism inspector, experiment picker. Each widget owns its rect, knows
how to draw itself, and returns True from `handle` when it was activated.
"""

import pygame

from ui import theme


class Label:
    def __init__(
        self,
        pos: tuple[int, int],
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int] = theme.TEXT_DIM,
    ) -> None:
        self.pos = pos  # midleft anchor
        self.font = font
        self.color = color
        self.text = text
        self.surface = font.render(text, True, color)

    def set_text(self, text: str) -> None:
        if text != self.text:
            self.text = text
            self.surface = self.font.render(text, True, self.color)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.surface, self.surface.get_rect(midleft=self.pos))


class Button:
    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        label: str,
        font: pygame.font.Font,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
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

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, theme.PANEL, self.rect, border_radius=6)
        pygame.draw.rect(surface, theme.ACCENT, self.rect, width=1, border_radius=6)
        text = self.font.render(self.label, True, theme.TEXT)
        surface.blit(text, text.get_rect(center=self.rect.center))


class Slider:
    """Horizontal slider; value snapped to `step` increments."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        font: pygame.font.Font,
        min_value: float,
        max_value: float,
        value: float,
        step: float = 0.25,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.font = font
        self.min = min_value
        self.max = max_value
        self.step = step
        self._value = value
        self._drag = False

    @property
    def value(self) -> float:
        return self._value

    def _set_from_x(self, x: int) -> None:
        t = max(0.0, min(1.0, (x - self.rect.left) / self.rect.width))
        raw = self.min + t * (self.max - self.min)
        self._value = round(raw / self.step) * self.step

    def _knob_x(self) -> int:
        t = (self._value - self.min) / (self.max - self.min)
        return self.rect.left + round(t * self.rect.width)

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._drag = self.rect.collidepoint(event.pos)
            if self._drag:
                self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self._drag:
            self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = False

    def draw(self, surface: pygame.Surface) -> None:
        y = self.rect.centery
        pygame.draw.line(surface, theme.PANEL_BORDER, (self.rect.left, y), (self.rect.right, y), 3)
        knob = self._knob_x()
        if knob > self.rect.left:
            pygame.draw.line(surface, theme.ACCENT, (self.rect.left, y), (knob, y), 3)
        pygame.draw.circle(surface, theme.ACCENT, (knob, y), 6)
        pygame.draw.circle(surface, theme.BG, (knob, y), 2)

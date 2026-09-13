"""The app's font stack, loaded once and passed down to the widgets.

`pygame.font.SysFont` needs system fonts, which the Pyodide (browser)
build does not have — there it returns a font that cannot render. So
every font is loaded through `_load`, which falls back to pygame's
bundled default. One bundle keeps sizes consistent across the UI.
"""

import pygame


def load_font(names: str, size: int, bold: bool = False) -> pygame.font.Font:
    try:
        font = pygame.font.SysFont(names, size, bold=bold)
        if font is not None:
            return font
    except Exception:
        pass
    return pygame.font.Font(None, size)


MONO = "dejavusansmono,consolas,dejavusansmono,monospace"
SANS = "dejavusans,verdana,arial,sans-serif"


class Fonts:
    """Every text style the interface uses."""

    def __init__(self) -> None:
        self.logo = load_font(SANS, 19, bold=True)
        self.tagline = load_font(SANS, 11)
        self.title = load_font(SANS, 12, bold=True)  # panel + section headers
        self.body = load_font(MONO, 13)  # stat values, readouts
        self.small = load_font(MONO, 11)  # labels, legends, ticker
        self.tiny = load_font(MONO, 10)  # chart axes
        self.button = load_font(SANS, 13, bold=True)
        self.metric = load_font(SANS, 22, bold=True)  # big stat-tile numbers
        self.keycap = load_font(MONO, 10, bold=True)

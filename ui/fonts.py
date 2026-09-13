# fonts, loaded once and passed round the UI.
# SysFont needs actual system fonts which the browser build does not have,
# so everything goes through load_font which falls back to the pygame one

import pygame


def load_font(names: str, size: int, bold: bool = False) -> pygame.font.Font:
    try:
        font = pygame.font.SysFont(names, size, bold=bold)
        if font is not None:
            return font
    except Exception:
        pass  # browser, or a machine with no fonts installed
    return pygame.font.Font(None, size)


MONO = "dejavusansmono,consolas,dejavusansmono,monospace"
SANS = "dejavusans,verdana,arial,sans-serif"


class Fonts:
    # one of each size/style the UI needs. if you add a new one put it here
    # instead of calling SysFont in the middle of the drawing code
    def __init__(self) -> None:
        self.logo = load_font(SANS, 19, bold=True)
        self.tagline = load_font(SANS, 11)
        self.title = load_font(SANS, 12, bold=True)  # panel headers
        self.body = load_font(MONO, 13)
        self.small = load_font(MONO, 11)
        self.tiny = load_font(MONO, 10)  # chart + trait labels
        self.button = load_font(SANS, 13, bold=True)
        self.metric = load_font(SANS, 22, bold=True)  # the big numbers
        self.keycap = load_font(MONO, 10, bold=True)

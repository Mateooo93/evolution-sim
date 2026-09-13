# fonts. the browser build has no system fonts at all so everything goes
# through load_font, which falls back to the one pygame ships with

import pygame

MONO = "dejavusansmono,consolas,dejavusansmono,monospace"
SANS = "dejavusans,verdana,arial,sans-serif"


def load_font(names: str, size: int, bold: bool = False) -> pygame.font.Font:
    try:
        font = pygame.font.SysFont(names, size, bold=bold)
        if font is not None:
            return font
    except Exception:
        pass
    return pygame.font.Font(None, size)


class Fonts:
    # all monospace apart from the logo. i tried mixing sans and mono for
    # the headers and it just looked like a website
    def __init__(self) -> None:
        self.logo = load_font(SANS, 18, bold=True)
        self.head = load_font(MONO, 12, bold=True)
        self.body = load_font(MONO, 12)
        self.small = load_font(MONO, 11)
        self.tiny = load_font(MONO, 10)


import pygame

from sim import AGGRESSION, SIZE, GENE_NAMES

BG = (255, 255, 255)
TEXT = (30, 35, 45)
DIM = (90, 100, 115)
FAINT = (150, 158, 170)
PANEL = (245, 247, 249)
BORDER = (200, 206, 214)
GREEN = (86, 182, 255)
AMBER = (212, 175, 55)
RED = (248, 113, 113)
GOLD = (200, 150, 0)
 
GRID = 64       # spacing of the faint lines on the plate

_font = None


def get_font(size=16):
    # making a font every frame is slow so keep one and reuse it
    global _font
    if _font is None:
        _font = pygame.font.Font(None, size)
    return _font


def clear(plate):
    # wipe the plate and draw faint squares on it so it isnt just empty black
    plate.fill(BG)
    for x in range(0, plate.get_width(), GRID):
        pygame.draw.line(plate, (235, 238, 242), (x, 0), (x, plate.get_height()))
    for y in range(0, plate.get_height(), GRID):
        pygame.draw.line(plate, (235, 238, 242), (0, y), (plate.get_width(), y))


def draw_panel(screen, rect):
    # only used for the replay bar
    pygame.draw.rect(screen, PANEL, rect)
    pygame.draw.rect(screen, BORDER, rect, width=1)


def fade(colour, amount):
    # mix a colour toward the background. used to show low energy, so it
    # works whether the background is dark or light
    return (int(colour[0] + (BG[0] - colour[0]) * amount),
            int(colour[1] + (BG[1] - colour[1]) * amount),
            int(colour[2] + (BG[2] - colour[2]) * amount))


def creature_colour(aggression, energy):
    # blue eats plants, red hunts, amber in between. low energy goes pale
    if aggression < 0.35:
        base = GREEN
    elif aggression < 0.7:
        base = AMBER
    else:
        base = RED
    if energy < 33:
        return fade(base, 0.7)
    if energy < 66:
        return fade(base, 0.35)
    return base


def draw_food(plate, food):
    for f in food:
        pygame.draw.circle(plate, AMBER, (int(f[0]), int(f[1])), 2)


def draw_creature(plate, x, y, energy, aggression, size):
    colour = creature_colour(aggression, energy)
    pygame.draw.circle(plate, colour, (int(x), int(y)), int(2 + size * 6))


def draw_trails(plate, world):
    # one short line behind each creature showing where it just came from
    for c in world.creatures:
        if len(c.trail) < 2:
            continue
        x0, y0 = c.trail[0]
        if abs(x0 - c.x) > 100 or abs(y0 - c.y) > 100:
            continue        # it wrapped round the edge, dont draw across the screen
        colour = creature_colour(c.genes[AGGRESSION], c.energy)
        pygame.draw.line(plate, fade(colour, 0.55),
                         (int(x0), int(y0)), (int(c.x), int(c.y)))


def draw_selection(plate, c):
    # plain ring round whatever you clicked
    pygame.draw.circle(plate, TEXT, (int(c.x), int(c.y)), int(2 + c.genes[SIZE] * 6) + 7, 1)


class Slider:
    # a line with a little handle you drag along it
    def __init__(self, x, y, width, low, high, value, step, colour):
        self.rect = pygame.Rect(x, y, width, 10)
        self.low = low
        self.high = high
        self.step = step
        self.colour = colour
        self.value = value
        self.dragging = False

    def set_from(self, x):
        part = max(0.0, min(1.0, (x - self.rect.left) / self.rect.width))
        raw = self.low + part * (self.high - self.low)
        self.value = round(raw / self.step) * self.step

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(0, 12).collidepoint(event.pos):
                self.dragging = True
                self.set_from(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

    def draw(self, screen, label, shown):
        font = get_font(15)
        y = self.rect.centery
        pygame.draw.line(screen, BORDER, (self.rect.left, y), (self.rect.right, y), 1)
        part = (self.value - self.low) / (self.high - self.low)
        knob = self.rect.left + int(part * self.rect.width)
        pygame.draw.rect(screen, self.colour, (knob - 2, y - 5, 4, 10))
        screen.blit(font.render(label, True, DIM), (self.rect.left, self.rect.top - 15))
        screen.blit(font.render(shown, True, self.colour), (self.rect.right + 6, y - 7))


def draw_header(screen, font, world, sliders, paused, replaying, fps):
    # no box, just text and a line under it
    screen.blit(font.render("EvoLab", True, GREEN), (12, 30))

    for slider, label, shown in sliders:
        slider.draw(screen, label, shown)

    if paused or replaying:
        word = "replay" if replaying else "paused"
        screen.blit(font.render(word, True, GOLD), (screen.get_width() - 90, 14))

    numbers = (f"pop {world.population()}   food {len(world.food)}   "
               f"gen {world.max_generation()}   born {world.births}   "
               f"starved {world.starved}   eaten {world.eaten}   killed {world.killed}   "
               f"agg {world.mean_aggression():.2f}   {fps:.0f}fps")
    screen.blit(font.render(numbers, True, DIM), (12, 56))
    pygame.draw.line(screen, BORDER, (0, 68), (screen.get_width(), 68))


def draw_help(screen, font, text):
    screen.blit(font.render(text, True, FAINT), (14, screen.get_height() - 22))


def draw_creature_info(screen, font, c):
    # when you click one, print its genes in the bottom left
    line = (f"#{id(c) % 10000}   gen {c.generation}   "
            f"energy {c.energy:.0f}   age {c.age:.0f}s")
    screen.blit(font.render(line, True, TEXT), (14, screen.get_height() - 74))
    genes = "   ".join(f"{name} {c.genes[i] * 100:.0f}" for i, name in enumerate(GENE_NAMES))
    screen.blit(font.render(genes, True, TEXT), (14, screen.get_height() - 56))
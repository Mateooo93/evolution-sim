# everything that gets drawn, plus the slider widget.
# pygame has no buttons or sliders so the slider here is hand made

import pygame

from sim import GENE_NAMES

# colours
BG = (11, 15, 20)
PANEL = (16, 22, 29)
BORDER = (29, 39, 51)
TEXT = (226, 232, 240)
DIM = (128, 144, 168)
FAINT = (78, 93, 113)
GREEN = (52, 211, 153)
RED = (248, 113, 113)
AMBER = (212, 175, 55)
GOLD = (250, 204, 21)

HEADER_H = 46


def draw_panel(screen, rect):
    pygame.draw.rect(screen, PANEL, rect)
    pygame.draw.rect(screen, BORDER, rect, width=1)


class Slider:
    # a line with a knob. value snaps to step so the numbers stay tidy
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
        # the name above it and the value to the right of it
        font = pygame.font.Font(None, 15)
        y = self.rect.centery
        pygame.draw.line(screen, BORDER, (self.rect.left, y), (self.rect.right, y), 2)
        knob = self.rect.left + int((self.value - self.low) / (self.high - self.low) * self.rect.width)
        pygame.draw.line(screen, self.colour, (self.rect.left, y), (knob, y), 2)
        pygame.draw.rect(screen, self.colour, (knob - 3, y - 6, 6, 12))
        screen.blit(font.render(label, True, DIM), (self.rect.left, self.rect.top - 16))
        screen.blit(font.render(shown, True, self.colour), (self.rect.right + 8, y - 7))


def draw_food(plate, food):
    for f in food:
        pygame.draw.circle(plate, AMBER, (int(f[0]), int(f[1])), 3)


def draw_creature(plate, x, y, energy, aggression, size):
    # colour goes green to red with aggression, brightness is energy,
    # radius is the size gene. that is the whole visual language
    bright = max(0.25, min(1.0, energy / 100))
    if aggression < 0.5:
        colour = blend(GREEN, AMBER, aggression * 2)
    else:
        colour = blend(AMBER, RED, (aggression - 0.5) * 2)
    colour = blend(BG, colour, bright)
    pygame.draw.circle(plate, colour, (int(x), int(y)), int(2 + size * 6))


def blend(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def draw_trails(plate, world):
    # a short tail behind each creature so you can see where it is going
    for c in world.creatures:
        if len(c.trail) < 2:
            continue
        colour = blend(GREEN, RED, c.genes[6])
        for i in range(len(c.trail) - 1):
            x1, y1 = c.trail[i]
            x2, y2 = c.trail[i + 1]
            if abs(x1 - x2) > 100 or abs(y1 - y2) > 100:
                continue    # it wrapped round the edge, dont draw across the screen
            pygame.draw.line(plate, blend(BG, colour, i / len(c.trail)),
                             (int(x1), int(y1)), (int(x2), int(y2)))


def draw_selection(plate, c):
    # ring round the creature you clicked
    r = int(2 + c.genes[1] * 6) + 7
    pygame.draw.circle(plate, (255, 255, 255), (int(c.x), int(c.y)), r, 1)


def draw_header(screen, font, world, sliders, paused, replaying, fps):
    rect = pygame.Rect(8, 8, screen.get_width() - 16, HEADER_H)
    draw_panel(screen, rect)
    screen.blit(font.render("EVOLAB", True, GREEN), (rect.left + 12, rect.top + 15))

    for slider, label, shown in sliders:
        slider.draw(screen, label, shown)

    if paused or replaying:
        word = "replay" if replaying else "paused"
        screen.blit(font.render(word, True, GOLD), (rect.right - 240, rect.top + 15))

    # one line of numbers along the bottom
    numbers = (f"pop {world.population()}   food {len(world.food)}   "
               f"gen {world.max_generation()}   born {world.births}   "
               f"starved {world.starved}   eaten {world.eaten}   killed {world.killed}   "
               f"agg {world.mean_aggression():.2f}   {fps:.0f}fps")
    screen.blit(font.render(numbers, True, DIM), (rect.left + 12, rect.bottom + 6))


def draw_help(screen, font, text):
    screen.blit(font.render(text, True, FAINT), (14, screen.get_height() - 22))


def draw_creature_info(screen, font, c):
    # when you click one, print its genes in the corner
    lines = [f"#{id(c) % 10000}  gen {c.generation}  energy {c.energy:.0f}  age {c.age:.0f}s"]
    lines.append("  ".join(f"{name} {c.genes[i] * 100:.0f}"
                           for i, name in enumerate(GENE_NAMES)))
    y = screen.get_height() - 74
    for line in lines:
        screen.blit(font.render(line, True, TEXT), (14, y))
        y += 18

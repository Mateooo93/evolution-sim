"""EvoLab — an artificial ecosystem simulator.

Run:  python main.py
Controls:  Space = pause/resume, mouse = pause button + speed slider.
"""

import argparse

import pygame

from rendering.renderer import Renderer
from simulation.ecosystem import Ecosystem, WorldConfig
from ui import theme
from ui.widgets import Button, Label, Slider

WIDTH, HEIGHT = 1280, 800

# Fixed simulation step in seconds (60 Hz game-logic tick).
STEP = 1 / 60
# Max steps caught up per frame — prevents the "spiral of death"
# when the window is dragged/backgrounded at high speed.
MAX_STEPS_PER_FRAME = 32


def main() -> int:
    parser = argparse.ArgumentParser(description="EvoLab — artificial ecosystem simulator")
    parser.add_argument(
        "--frames", type=int, default=0,
        help="quit after N rendered frames (0 = run until closed)",
    )
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("EvoLab")
    font = pygame.font.SysFont("dejavusansmono,consolas,monospace", 14)
    logo_font = pygame.font.SysFont("dejavusans,verdana,sans-serif", 14, bold=True)
    clock = pygame.time.Clock()

    world = Ecosystem(
        WorldConfig(
            width=WIDTH, height=HEIGHT, organisms=80,
            wander_turn_rate=1.6,
        )
    )
    renderer = Renderer(screen)

    # --- header chrome -------------------------------------------------
    header = pygame.Rect(12, 12, WIDTH - 24, 46)
    cy = header.centery
    logo = Label((header.left + 16, cy), "EVOLAB", logo_font, theme.ACCENT)
    population = Label((146, cy), "Population: 80", font)
    food = Label((300, cy), "Food: 0", font)
    traits = Label((420, cy), "avg speed 50%  size 50%", font)
    pause_btn = Button((640, cy - 14, 100, 28), "Pause", font)
    speed_value = Label((WIDTH - 416, cy), "1.0x", font)
    speed_slider = Slider((WIDTH - 360, cy - 8, 200, 16), font, 0.25, 20.0, 1.0)
    hint = Label((WIDTH - 132, cy), "Space", font, theme.PANEL_BORDER)

    paused = False
    accumulator = 0.0
    frame = 0

    running = True
    while running:
        # dt in seconds, clamped so a long stall doesn't teleport the sim
        dt = min(clock.tick(60) / 1000.0, 0.25)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                paused = not paused
            if pause_btn.handle(event):
                paused = not paused
            speed_slider.handle(event)

        if not paused:
            # fixed timestep with accumulator: speed scales the number of
            # steps per real second, never the size of a step
            accumulator += dt * speed_slider.value
            steps = 0
            while accumulator >= STEP and steps < MAX_STEPS_PER_FRAME:
                world.update(STEP)
                accumulator -= STEP
                steps += 1
            if steps == MAX_STEPS_PER_FRAME:
                accumulator = 0.0  # drop the backlog

        renderer.render(world)

        # --- chrome -----------------------------------------------------
        pygame.draw.rect(screen, theme.PANEL, header, border_radius=8)
        pygame.draw.rect(screen, theme.PANEL_BORDER, header, width=1, border_radius=8)
        population.set_text(f"Population: {len(world.organisms)}")
        food.set_text(f"Food: {len(world.food)}")
        speed_value.set_text(f"{speed_slider.value:.1f}x")
        traits.set_text(
            f"avg speed {round(world.trait_average('speed') * 100)}%"
            f"  size {round(world.trait_average('size') * 100)}%"
        )
        logo.draw(screen)
        population.draw(screen)
        food.draw(screen)
        traits.draw(screen)
        speed_value.draw(screen)
        speed_slider.draw(screen)
        pause_btn.draw(screen)
        hint.draw(screen)

        pygame.display.flip()
        frame += 1
        if args.frames and frame >= args.frames:
            running = False

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

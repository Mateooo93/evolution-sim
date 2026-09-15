# the app. the window, the clock, the sliders and the replay.
# the world itself is in sim.py and everything drawn is in ui.py

import asyncio
import sys
from collections import deque

import pygame

import sim
import ui

WIDTH, HEIGHT = 1280, 860
TOP = 74                # height of the header strip along the top
STEP = 1 / 60           # the world always moves in 1/60 second steps
SNAP_EVERY = 0.25       # seconds between replay frames
SNAP_MAX = 240          # about a minute of them
IN_BROWSER = sys.platform == "emscripten"


async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("EvoLab")
    plate = pygame.Surface((WIDTH, HEIGHT - TOP))    # the world is drawn here
    font = pygame.font.Font(None, 16)
    clock = pygame.time.Clock()

    world = sim.World(WIDTH, HEIGHT - TOP, start=90)

    # the four sliders. food and aggression change the world, speed and
    # mutation change how it runs
    food_slider = ui.Slider(430, 30, 120, 0.1, 2.5, 1.0, 0.05, ui.AMBER)
    pressure_slider = ui.Slider(620, 30, 120, -1.0, 1.0, 0.0, 0.05, ui.RED)
    speed_slider = ui.Slider(810, 30, 120, 0.25, 20.0, 1.0, 0.25, ui.GREEN)
    mutation_slider = ui.Slider(1000, 30, 120, 0.001, 0.20, 0.05, 0.001, ui.TEXT)
    sliders = [food_slider, pressure_slider, speed_slider, mutation_slider]
    scrub = ui.Slider(120, HEIGHT - 34, WIDTH - 260, 0, SNAP_MAX - 1, 0, 1, ui.GOLD)

    frames = deque(maxlen=SNAP_MAX)
    selected = None
    paused = False
    replaying = False
    replay_at = 0
    steps = 0
    snap_acc = 0.0
    replay_acc = 0.0
    drawn = 0
    running = True

    while running:
        # dt is how long the last frame took, clamped so dragging the window
        # about does not jump the world forward
        if IN_BROWSER:
            await asyncio.sleep(1 / 60)      # in a browser you cannot block
            dt = min(clock.tick(0) / 1000.0, 0.25)
        else:
            dt = min(clock.tick(60) / 1000.0, 0.25)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r and frames:
                    replaying = not replaying
                    replay_at = 0
                    paused = replaying
                elif event.key == pygame.K_ESCAPE and replaying:
                    replaying = False
                elif event.key == pygame.K_LEFT and replaying:
                    replay_at = max(0, replay_at - 1)
                elif event.key == pygame.K_RIGHT and replaying:
                    replay_at = min(len(frames) - 1, replay_at + 1)
            for slider in sliders:
                slider.handle(event)
            if replaying:
                scrub.handle(event)
                if scrub.dragging:
                    replay_at = int(scrub.value)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                x, y = event.pos
                if y > TOP and not any(s.rect.inflate(0, 16).collidepoint(x, y) for s in sliders):
                    selected = world.creature_at(x, y - TOP)
                    if selected is None:
                        selected = None   # clicked nothing, so nothing selected

        # the sliders write straight into the world
        world.food_rate = sim.FOOD_RATE * food_slider.value
        world.pressure = pressure_slider.value
        world.mutation = mutation_slider.value

        if replaying and frames:
            # play the recording back, unless the handle is being dragged
            if not scrub.dragging:
                replay_acc += dt * speed_slider.value
                while replay_acc >= 0.1:
                    replay_acc -= 0.1
                    replay_at = (replay_at + 1) % len(frames)
                scrub.value = replay_at
            frame = frames[replay_at]
        else:
            if not paused:
                # run the world in whole 1/60 second steps. the speed slider
                # changes how many steps per second, never the step size
                steps += dt * speed_slider.value
                while steps >= STEP:
                    steps -= STEP
                    world.update(STEP)
                snap_acc += dt * speed_slider.value
                while snap_acc >= SNAP_EVERY:
                    snap_acc -= SNAP_EVERY
                    frames.append(sim.snapshot(world))
            if selected is not None and selected.dead:
                selected = None
            frame = None

        # --- draw ---------------------------------------------------------
        plate.fill(ui.BG)
        if frame is None:
            ui.draw_food(plate, world.food)
            ui.draw_trails(plate, world)
            for c in world.creatures:
                ui.draw_creature(plate, c.x, c.y, c.energy,
                                 c.genes[sim.AGGRESSION], c.genes[sim.SIZE])
            if selected is not None:
                ui.draw_selection(plate, selected)
        else:
            ui.draw_food(plate, frame["food"])
            for x, y, energy, aggression, size in frame["creatures"]:
                ui.draw_creature(plate, x, y, energy, aggression, size)

        screen.fill(ui.BG)
        screen.blit(plate, (0, TOP))
        ui.draw_header(screen, font, world, [
            (food_slider, "food", f"{food_slider.value:.2f}x"),
            (pressure_slider, "aggression", f"{pressure_slider.value:+.2f}"),
            (speed_slider, "speed", f"{speed_slider.value:.2f}x"),
            (mutation_slider, "mutation", f"{mutation_slider.value * 100:.1f}%"),
        ], paused, replaying, clock.get_fps())

        if replaying:
            bar = pygame.Rect(8, HEIGHT - 56, WIDTH - 16, 44)
            ui.draw_panel(screen, bar)
            screen.blit(font.render("replay", True, ui.GOLD), (20, HEIGHT - 32))
            scrub.draw(screen, "", "")
            screen.blit(font.render(f"{replay_at + 1}/{len(frames)}", True, ui.TEXT),
                        (WIDTH - 90, HEIGHT - 32))
        elif selected is not None:
            ui.draw_creature_info(screen, font, selected)
        else:
            ui.draw_help(screen, font, "space pause,  r replay the last minute,  click a creature")

        pygame.display.flip()
        drawn += 1

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

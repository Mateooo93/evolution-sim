"""EvoLab — an artificial ecosystem simulator.

Run:  python main.py
Controls:  Space = pause/resume, mouse = pause button, speed and
mutation-rate sliders.
"""

import argparse
import asyncio
import sys

import pygame

from rendering.renderer import Renderer
from simulation.ecosystem import Ecosystem, WorldConfig
from ui import theme
from ui.inspector import Inspector
from ui.widgets import Button, Label, Slider

# True under PyScript/Pyodide (WebAssembly) — the browser drives the
# frame timing, so the loop must yield with `await` instead of blocking.
IN_BROWSER = sys.platform == "emscripten"

WIDTH, HEIGHT = 1280, 800

# Fixed simulation step in seconds (60 Hz game-logic tick).
STEP = 1 / 60
# Max steps caught up per frame — prevents the "spiral of death"
# when the window is dragged/backgrounded at high speed.
MAX_STEPS_PER_FRAME = 32

def _load_font(names: str, size: int, bold: bool = False):
    """SysFont on desktop; falls back to pygame's bundled font where
    system fonts are unavailable (e.g. the Pyodide web build)."""
    try:
        f = pygame.font.SysFont(names, size, bold=bold)
        if f is not None:
            return f
    except Exception:
        pass
    return pygame.font.Font(None, size)


async def main() -> int:
    parser = argparse.ArgumentParser(description="EvoLab — artificial ecosystem simulator")
    parser.add_argument(
        "--frames", type=int, default=0,
        help="quit after N rendered frames (0 = run until closed)",
    )
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    font = _load_font("dejavusansmono,consolas,monospace", 14)
    logo_font = _load_font("dejavusans,verdana,sans-serif", 14, bold=True)
    clock = pygame.time.Clock()

    world = Ecosystem(
        WorldConfig(
            width=WIDTH, height=HEIGHT, organisms=80,
            wander_turn_rate=1.6,
        )
    )
    renderer = Renderer(screen)
    inspector = Inspector(font)
    selected: object | None = None  # the Organism currently picked

    # --- header chrome -------------------------------------------------
    header = pygame.Rect(12, 12, WIDTH - 24, 46)
    cy = header.centery
    logo = Label((header.left + 16, cy), "EVOLAB", logo_font, theme.ACCENT)
    population = Label((140, cy), "Population: 80", font)
    food = Label((272, cy), "Food: 0", font)
    generation = Label((362, cy), "Gen: 1", font)
    traits = Label((444, cy), "avg speed 50%  size 50%", font)
    pause_btn = Button((650, cy - 14, 100, 28), "Pause", font)
    mut_label = Label((764, cy), "mut", font, theme.TEXT_DIM)
    mut_slider = Slider((798, cy - 8, 110, 16), font, 0.001, 0.20, 0.05, step=0.001)
    mut_value = Label((914, cy), "5.0%", font)
    speed_value = Label((966, cy), "1.0x", font)
    speed_slider = Slider((1006, cy - 8, 170, 16), font, 0.25, 20.0, 1.0)

    paused = False
    accumulator = 0.0
    frame = 0

    def _on_widget(pos: tuple[int, int]) -> bool:
        """True if a click point is over the header chrome (where sliders
        and the pause button live), so plate-clicks don't steal focus."""
        if header.collidepoint(pos):
            return True
        return any(w.rect.collidepoint(pos) for w in (pause_btn, mut_slider, speed_slider))

    running = True
    while running:
        # dt in seconds, clamped so a long stall doesn't teleport the sim.
        # In the browser the page drives the frame: yield to the event loop
        # and measure elapsed time instead of blocking on the clock.
        if IN_BROWSER:
            await asyncio.sleep(1 / 60)
            dt = min(clock.tick(0) / 1000.0, 0.25)
        else:
            dt = min(clock.tick(60) / 1000.0, 0.25)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                paused = not paused
            if pause_btn.handle(event):
                paused = not paused
            speed_slider.handle(event)
            mut_slider.handle(event)

            # Click on the plate to select an organism (or clear any
            # selection when clicking empty space, away from the widgets).
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not _on_widget(event.pos):
                    picked = world.organism_at(event.pos[0], event.pos[1], tolerance=2)
                    selected = picked if picked is not None else None

        world.config.mutation_rate = mut_slider.value

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

        sel = selected if selected is not None and selected in world.organisms else None
        renderer.render(world, selected=sel)
        if sel is not None:
            renderer.draw_selected_banner(sel, font)
            inspector.draw(screen, sel, world.config)

        # --- chrome -----------------------------------------------------
        pygame.draw.rect(screen, theme.PANEL, header, border_radius=8)
        pygame.draw.rect(screen, theme.PANEL_BORDER, header, width=1, border_radius=8)
        population.set_text(f"Population: {len(world.organisms)}")
        food.set_text(f"Food: {len(world.food)}")
        generation.set_text(f"Gen: {max((o.generation for o in world.organisms), default=0)}")
        speed_value.set_text(f"{speed_slider.value:.1f}x")
        mut_value.set_text(f"{mut_slider.value * 100:.1f}%")
        traits.set_text(
            f"avg speed {round(world.trait_average('speed') * 100)}%"
            f"  size {round(world.trait_average('size') * 100)}%"
            f"  agg {round(world.trait_average('aggression') * 100)}%"
        )
        logo.draw(screen)
        population.draw(screen)
        food.draw(screen)
        generation.draw(screen)
        traits.draw(screen)
        mut_label.draw(screen)
        mut_slider.draw(screen)
        mut_value.draw(screen)
        speed_value.draw(screen)
        speed_slider.draw(screen)
        pause_btn.draw(screen)

        pygame.display.flip()
        frame += 1
        if args.frames and frame >= args.frames:
            running = False

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

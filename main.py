"""EvoLab — an artificial ecosystem simulator.

Run:  python main.py
Controls:  Space = pause/resume; R = replay the last minute (time machine);
Esc = stop replay; mouse = pause/Replay buttons, speed & mutation sliders.
"""

import argparse
import asyncio
import sys
from collections import deque

import pygame

from rendering.renderer import Renderer
from simulation.ecosystem import Ecosystem, WorldConfig
from simulation.snapshot import capture as capture_snapshot
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
    replay_btn = Button((1178, cy - 14, 80, 28), "Replay", font)

    paused = False
    accumulator = 0.0
    frame = 0

    # --- time machine (replay) state ----------------------------------
    # Snapshots of the world taken every SNAP_INTERVAL sim-seconds, kept in
    # a bounded ring. Press R (or the Replay button) to enter replay; drag
    # the scrub slider (under the header) to scrub through the recording.
    SNAP_INTERVAL = 0.25
    SNAP_MAX = 240  # ~60s of history
    snapshots: deque = deque(maxlen=SNAP_MAX)
    _snap_acc = 0.0
    replaying = False
    replay_idx = 0
    _manual_seek = False  # user grabbed the scrubber; stop auto-advance
    _replay_acc = 0.0
    _replay_step = 0.10  # sim-seconds per snapshot while auto-playing
    # Scrub bar spanning the recorded window, shown only while replaying.
    replay_slider = Slider(
        (16, 64, WIDTH - 32, 14), font, 0, SNAP_MAX - 1, 0, step=1,
    )

    def _on_widget(pos: tuple[int, int]) -> bool:
        """True if a click point is over the header chrome (where sliders
        and buttons live), so plate-clicks don't steal focus."""
        if header.collidepoint(pos):
            return True
        return any(w.rect.collidepoint(pos) for w in (pause_btn, mut_slider, speed_slider, replay_btn))

    def _toggle_replay() -> None:
        nonlocal replaying, replay_idx, _replay_acc, _manual_seek
        if not snapshots:
            return
        if not replaying:
            # The scrubber spans exactly what we've recorded, so the end
            # of the bar is always the newest frame (no dead space).
            replay_slider.max = max(1, len(snapshots) - 1)
            replaying = True
            paused = True
            replay_idx = 0
            _replay_acc = 0.0
            _manual_seek = False
            replay_slider.value = 0.0
        else:
            replaying = False
            replay_idx = 0

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
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                _toggle_replay()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if replaying:
                    _toggle_replay()
            elif event.type == pygame.KEYDOWN and replaying:
                if event.key == pygame.K_LEFT and snapshots:
                    _manual_seek = True
                    replay_idx = max(0, replay_idx - 1)
                    replay_slider.value = float(replay_idx)
                elif event.key == pygame.K_RIGHT and snapshots:
                    _manual_seek = True
                    replay_idx = min(len(snapshots) - 1, replay_idx + 1)
                    replay_slider.value = float(replay_idx)
            if pause_btn.handle(event):
                paused = not paused
            speed_slider.handle(event)
            mut_slider.handle(event)
            if replaying:
                replay_slider.handle(event)
                if replay_slider.dragging:
                    # Scrub to the dragged frame and pause auto-play.
                    _manual_seek = True
                    replay_idx = min(len(snapshots) - 1, int(replay_slider.value))
            if replay_btn.handle(event):
                _toggle_replay()

            # Click on the plate to select an organism (or clear any
            # selection when clicking empty space, away from the widgets).
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not _on_widget(event.pos):
                    picked = world.organism_at(event.pos[0], event.pos[1], tolerance=2)
                    selected = picked if picked is not None else None

        world.config.mutation_rate = mut_slider.value

        if replaying:
            if _manual_seek:
                # The user is scrubbing: the slider position is the frame.
                replay_idx = min(len(snapshots) - 1, max(0, int(replay_slider.value)))
            else:
                # Auto-play: advance the playhead; move the knob along.
                _replay_acc += dt * speed_slider.value
                while _replay_acc >= _replay_step and snapshots:
                    _replay_acc -= _replay_step
                    replay_idx += 1
                    if replay_idx >= len(snapshots):
                        replay_idx = 0  # loop
                replay_slider.value = float(replay_idx)
            replay_frame = snapshots[replay_idx]
            renderer.render(world, selected=None, snapshot=replay_frame)
        else:
            if not paused:
                # fixed timestep with accumulator: speed scales the number
                # of steps per real second, never the size of a step
                accumulator += dt * speed_slider.value
                steps = 0
                while accumulator >= STEP and steps < MAX_STEPS_PER_FRAME:
                    world.update(STEP)
                    accumulator -= STEP
                    steps += 1
                if steps == MAX_STEPS_PER_FRAME:
                    accumulator = 0.0  # drop the backlog

            # Record a snapshot for the time machine on a bounded cadence.
            _snap_acc += dt * (speed_slider.value if not paused else 0.0)
            while _snap_acc >= SNAP_INTERVAL:
                _snap_acc -= SNAP_INTERVAL
                snapshots.append(capture_snapshot(world))

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
            f"spd {round(world.trait_average('speed') * 100)}%"
            f"  sz {round(world.trait_average('size') * 100)}%"
            f"  ag {round(world.trait_average('aggression') * 100)}%"
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
        replay_btn.draw(screen)

        # Time-machine scrub bar: a panel under the header with a labelled
        # slider spanning the recording. Drag it to hunt for a moment.
        if replaying and snapshots:
            scrub = pygame.Rect(12, 52, WIDTH - 24, 34)
            pygame.draw.rect(screen, theme.PANEL, scrub, border_radius=6)
            pygame.draw.rect(screen, theme.PREDATOR, scrub, width=1, border_radius=6)
            pos = font.render(f"{replay_idx + 1} / {len(snapshots)}", True, theme.TEXT)
            screen.blit(pos, pos.get_rect(midright=(scrub.right - 8, scrub.centery)))
            replay_slider.draw(screen)

        pygame.display.flip()
        frame += 1
        if args.frames and frame >= args.frames:
            running = False

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

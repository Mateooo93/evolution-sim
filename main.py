# EvoLab. run it with:  python main.py
#
# controls: SPACE pause, R replay the last minute, ESC out of replay,
# click a creature to inspect it, and the header sliders do speed /
# mutation / food / aggression
#
# this file is just the shell: it owns the clock, the window, the
# selection and the time machine. the world lives in simulation/, the
# drawing in rendering/ and ui/, and none of them know about each other

import argparse
import asyncio
import math  # left over from an old idea, not used
import sys
from collections import deque

import pygame

from rendering.renderer import Renderer
from simulation.ecosystem import Ecosystem, WorldConfig
from simulation.snapshot import capture as capture_snapshot
from ui import theme
from ui.fonts import Fonts
from ui.hud import HEIGHT, WIDTH, Hud, Replay

# the sim always runs in 1/60s chunks. the SPEED slider changes how many
# chunks per second, never the size of a chunk, so 0.25x and 20x behave
# exactly the same, just faster or slower
STEP = 1 / 60
# cap the catch up. drag the window about at 20x and come back and it
# would otherwise try to simulate a week in one frame
MAX_STEPS_PER_FRAME = 32

# time machine: how often we save a frame and how many we keep
SNAP_INTERVAL = 0.25
SNAP_MAX = 240      # roughly a minute
REPLAY_STEP = 0.10  # sim seconds per saved frame while playing back

# True in the browser (pyscript = wasm). we cant block on clock.tick
# there, the page drives the frames so we await instead
IN_BROWSER = sys.platform == "emscripten"


async def main() -> int:
    parser = argparse.ArgumentParser(description="EvoLab — artificial ecosystem simulator")
    parser.add_argument(
        "--frames", type=int, default=0,
        help="quit after N rendered frames (0 = run until closed)",
    )
    parser.add_argument(
        "--shot", default="", metavar="PATH",
        help="save the last rendered frame to PATH (headless verification)",
    )
    parser.add_argument(
        "--seed", type=int, default=0, help="seed the world's randomness (0 = any)",
    )
    args = parser.parse_args()
    if args.shot and not args.frames:
        args.frames = 240  # give the world a few seconds before the shot
    if args.seed:
        import random

        random.seed(args.seed)

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("EvoLab")
    fonts = Fonts()
    clock = pygame.time.Clock()

    # --- state ----------------------------------------------------------
    paused = False
    selected = None  # the Organism currently picked
    kin: frozenset[int] = frozenset()
    _kin_key = None  # (selected id, births) the cached kin set was built for
    accumulator = 0.0
    frame = 0

    # --- the time machine -----------------------------------------------
    snapshots: deque = deque(maxlen=SNAP_MAX)
    _snap_acc = 0.0
    replaying = False
    replay_idx = 0
    _manual_seek = False  # user grabbed the scrubber; stop auto-advance
    _replay_acc = 0.0

    def toggle_pause() -> None:
        nonlocal paused
        paused = not paused

    def toggle_replay() -> None:
        # in and out of the time machine
        nonlocal replaying, replay_idx, _replay_acc, _manual_seek, paused
        if not snapshots:
            return
        if not replaying:
            # going into replay pauses the live world
            replaying = True
            paused = True
            replay_idx = 0
            _replay_acc = 0.0
            _manual_seek = False
            hud.set_replay_span(len(snapshots))
        else:
            replaying = False
            replay_idx = 0

    # jump the replay to a frame
    def seek(index: int) -> None:
        nonlocal replay_idx, _manual_seek
        if not snapshots:
            return
        _manual_seek = True
        replay_idx = min(len(snapshots) - 1, max(0, index))

    def pick(x: int, y: int) -> None:
        # click the plate = select whatever is under the cursor.
        # clicking empty space clears it
        nonlocal selected
        selected = world.organism_at(x, y, tolerance=3)

    hud = Hud((WIDTH, HEIGHT), fonts, toggle_pause, toggle_replay, seek)

    # the world is exactly the size of the plate the layout left for it
    world = Ecosystem(
        WorldConfig(
            width=hud.plate.width,
            height=hud.plate.height,
            organisms=90,
            wander_turn_rate=1.6,
        )
    )
    renderer = Renderer(hud.plate.size)

    running = True
    while running:
        # dt in seconds, clamped to 0.25 so a stall (window drag, laptop
        # waking up) cant teleport the world forwards
        if IN_BROWSER:
            await asyncio.sleep(1 / 60)
            dt = min(clock.tick(0) / 1000.0, 0.25)
        else:
            dt = min(clock.tick(60) / 1000.0, 0.25)
        mouse = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    toggle_pause()
                elif event.key == pygame.K_r:
                    toggle_replay()
                elif event.key == pygame.K_ESCAPE and replaying:
                    toggle_replay()
                elif event.key == pygame.K_LEFT and replaying:
                    seek(replay_idx - 1)
                    hud.scrub.value = float(replay_idx)
                elif event.key == pygame.K_RIGHT and replaying:
                    seek(replay_idx + 1)
                    hud.scrub.value = float(replay_idx)
            hud.handle(event, replaying)
            # Clicking the plate (not the chrome) picks a creature.
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and hud.plate.collidepoint(event.pos)
                    and not hud.chrome_at(event.pos, replaying)):
                pick(event.pos[0] - hud.plate.left, event.pos[1] - hud.plate.top)

        world.config.mutation_rate = hud.mutation
        world.config.food_supply_scale = hud.food_scale
        world.config.aggression_pressure = hud.pressure
        events = world.take_events()
        screen.fill(theme.BG)

        if replaying:
            # move the playhead and draw a stored frame instead of the world
            if _manual_seek:
                replay_idx = min(len(snapshots) - 1, max(0, int(hud.scrub.value)))
            else:
                _replay_acc += dt * hud.speed
                while _replay_acc >= REPLAY_STEP:
                    _replay_acc -= REPLAY_STEP
                    replay_idx += 1
                    if replay_idx >= len(snapshots):
                        replay_idx = 0  # loop it
                hud.scrub.value = float(replay_idx)
            renderer.render(world, snapshot=snapshots[replay_idx], dt=dt)
        else:
            if not paused:
                # the accumulator: add the real time (times the speed
                # slider) and run whole 1/60 steps off the total
                accumulator += dt * hud.speed
                steps = 0
                while accumulator >= STEP and steps < MAX_STEPS_PER_FRAME:
                    world.update(STEP)
                    accumulator -= STEP
                    steps += 1
                if steps == MAX_STEPS_PER_FRAME:
                    accumulator = 0.0  # we are behind, bin the backlog

                # save a frame for the time machine every 0.25 sim seconds
                _snap_acc += dt * hud.speed
                while _snap_acc >= SNAP_INTERVAL:
                    _snap_acc -= SNAP_INTERVAL
                    snapshots.append(capture_snapshot(world))

            # if the creature we had selected died, forget it
            if selected is not None and selected.dead:
                selected = None
            # recompute the family rings only when something could have
            # changed (a birth or a new creature clicked). doing it every
            # frame meant walking the whole population 60x a second
            key = (selected.id, world.births, len(world.organisms)) if selected else None
            if key != _kin_key:
                _kin_key = key
                kin = world.lineage_members(selected.lineage) if selected else frozenset()
            renderer.consume(events)
            renderer.render(world, selected=selected, kin=kin, dt=dt)

        hud.consume(events, world.time, world.max_generation)
        renderer.present(screen, hud.plate)
        hud.draw(screen, world, selected, kin, paused,
                 Replay(replay_idx, len(snapshots)) if (replaying and snapshots) else None,
                 clock.get_fps(), mouse)
        pygame.display.flip()

        frame += 1
        if args.frames and frame >= args.frames:
            running = False

    if args.shot:
        # dev flag, saves the last frame so i can look at it without a
        # monitor attached
        pygame.image.save(screen, args.shot)
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

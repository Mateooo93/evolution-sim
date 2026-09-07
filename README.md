# EvoLab

An interactive artificial-life simulator: virtual organisms compete for
resources, reproduce, mutate, and evolve. Watch natural selection in real
time, manipulate the environment, and run evolution experiments.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Controls: `Space` pauses, the header has a pause button and a speed slider.

## Architecture

- `simulation/` — pure Python, no pygame: `Ecosystem` holds all state and
  only knows how to advance by `dt` seconds. The UI owns the clock.
  Organisms carry an 8-trait `Genome`; energy drains from metabolism,
  movement and body upkeep (trait tradeoffs), and they die of starvation
  or old age. Until food + reproduction land, a slow stream of random
  immigrants keeps the lab population from emptying.
- `rendering/` — draws ecosystem state onto the screen (static background
  is pre-rendered, blitted every frame). Body radius = size, brightness =
  energy, heading tick length = speed, so selection is visible on the plate.
- `ui/` — hand-drawn widgets (button, slider, label) and the theme palette.

The simulation advances on a fixed 60 Hz timestep with an accumulator;
the speed control scales how many steps run per real second, never the
step size.

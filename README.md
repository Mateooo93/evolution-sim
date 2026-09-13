# EvoLab

An interactive artificial-life simulator: virtual organisms forage, hunt,
reproduce, mutate and evolve on a finite plate, and you watch natural
selection happen in real time. Click any creature to read its genome and
its family line, wake up the environment with the speed and mutation
sliders, or rewind the last minute and find the moment a lineage died.

## Run

```bash
python3 -m venv .venv
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

(`ensurepip` guards against systems where `venv` is created without pip —
common on Ubuntu/Pop!_OS without the `python3-venv` package. If it
errors, run `sudo apt install -y python3-venv python3-pip` first.)

### Controls

| Control | What it does |
| --- | --- |
| `Space` | pause / resume |
| `R` | enter or leave the time machine (rewind the last ~60 s) |
| `←` `→` | while replaying, step one recorded frame |
| `Esc` | leave replay |
| click a creature | select it: a reticle marks it, the panel shows its genome, energy, age and line |
| click empty plate | deselect |

The header carries the pause and replay buttons, a speed slider
(0.25×–20×, the simulator runs as fast as the machine manages) and the
per-birth mutation rate.

## Reading the plate

Nothing on the plate needs explaining to be useful — that was the design
goal from the first commit:

| You see | It means |
| --- | --- |
| body radius | `size` trait |
| body brightness | energy — a dim cell is starving |
| heading tick length | `speed` trait |
| colour, green → amber → red | `aggression`: pure forager → hunter |
| thin ring around a cell | ready to mate |
| fading tail | where it has just been, tinted by aggression, so a hunt is a streak |
| expanding amber ring | a meal was eaten |
| expanding red ring | a kill |
| white reticle + ring | the selected creature |
| dim green rings | the selected creature's living family line |

## The lab panels

- **ECOSYSTEM** — population, standing food, deepest generation, births
  and deaths, plus a bar showing how the plate divides between foragers,
  mixed feeders and hunters.
- **TRENDS** — population, food and mean aggression over the last five
  minutes, normalised to their own ranges. This is where evolution is
  visible as a shape rather than a number: watch mean aggression drift up
  as hunters appear, or the population breathe as food runs down.
- **RECENT** — an event log. Kills are logged as they happen (both ids),
  everything else is summarised once per simulated second. A new deepest
  generation gets its own line.
- **SELECTED** — the specimen: the creature drawn as the plate draws it,
  its role and family line, energy / age / readiness meters, and all eight
  traits as bars with a tick marking the population average on each, so
  "is this one fast for its time?" is answerable at a glance.

## Play in your browser

`web/` holds a browser build of the same game. PyScript runs Python (and
pygame) as WebAssembly inside the page — no server, no install, works on
any static host. The first load takes a few seconds while it pays for
Python from the CDN.

```bash
cd web
python3 -m http.server 8000
# open http://localhost:8000
```

`web/evolab.py` is generated from the project sources by `web/build.py` —
re-run it after changing any module:

```bash
.venv/bin/python web/build.py
```

### Deploy to GitHub Pages

```bash
# from the repo root
git remote add origin git@github.com:YOURNAME/evolution-sim.git
git push -u origin master
git subtree push --prefix web origin gh-pages
```

Then in the GitHub repo: **Settings → Pages → Build and deployment →
Source: Deploy from a branch**, pick `gh-pages` / `(root)`. The game goes
live at `https://YOURNAME.github.io/evolution-sim/`.

## Architecture

- `simulation/` — pure Python, no pygame: `Ecosystem` holds all state and
  only knows how to advance by `dt` seconds. The UI owns the clock.
  - `genome.py` — eight heritable traits in [0, 1] and their phenotype
    mapping. Higher is not better: each trait carries a price.
  - `ecosystem.py` — the rules (energy, sensing, predation, mating,
    immigration), the per-second `Sample` history the chart reads, and an
    `Event` stream so the view layers can react to what happened without
    reaching into the world.
  - `spatial.py` — a toroidal hash grid, rebuilt each tick, answering
    "nearest neighbour within r" in O(1)-ish time. Food has its own grid.
  - `snapshot.py` — cheap render-only copies of the world, so the time
    machine can show a past frame without touching the live simulation.
- `rendering/` — a dumb view: `renderer.py` paints the world onto its own
  plate surface (the app blits it into the layout), `orbs.py` holds the
  colour model and the pre-rendered orb sprites shared with the inspector.
- `ui/` — `theme.py` (palette and metrics), `fonts.py` (one font stack,
  with a fallback for the browser), `widgets.py` (button, slider, meter,
  tiles), `charts.py` (trends), `inspector.py` (the specimen panel) and
  `hud.py` (layout, chrome, input routing).
- `tests/` — the simulation contracts, stepping the world directly:

  ```bash
  .venv/bin/python -m unittest discover -s tests -v
  ```

The simulation advances on a fixed 60 Hz timestep with an accumulator;
the speed control scales how many steps run per real second, never the
step size.

## The ecology, in numbers

The plate is a flow, not a stock. Food arrives in **patches** (a clump of
items, a meadow) at a fixed supply rate, and the population settles where
consumption meets supply — around 180–240 creatures on the default plate
at the shipped constants, swinging between roughly 120 and 270 over a long
run as booms and busts play out.

Per-organism energy:

```
drain/s = (0.22 + 0.40·metabolism) × (1 + 0.9·speed + 0.8·size)
          × (1 − 0.5·efficiency) × (1 + 0.3·aggression)
```

Three rules matter more than the constants:

- **Hunting is an endurance chase.** A hunter only targets prey it can
  out-run, and prey only panic at a threat that is close *and* faster
  than they are. A sprint needs energy in the tank, so a fresh, alert
  prey escapes a hunter of similar speed and a tired one does not. Speed
  decides, and both sides pay for it.
- **Hunting costs, carrying the gene doesn't.** The chase burns extra
  energy, so predation has to pay for itself; an aggression gene that is
  never used is nearly free. This keeps the climb smooth — a mutant that
  hunts a little pays a little — instead of digging a fitness valley no
  intermediate can cross.
- **Specialists win, generalists don't.** A harsh gut is bad at plants
  (`forage_penalty`), so mid-aggression creatures are mediocre at both
  trades and the population holds a grazer majority with a hunting tail.

A slow stream of random immigrants (below 28 creatures, at 0.15/s) remains
as an extinction safety net. It arrives as foragers — a dying world is
reseeded with prey, not handed a population of hunters — and in a healthy
run it never fires at all.

What the world does on its own: the population stabilises and breathes,
mean aggression sits low with a steady trickle of successful hunts, and
selection visibly drives mean speed up and body size down (the trends
chart shows it). A specialist predator *caste* does not emerge — the
aggression continuum settles at a mixed strategy instead. That is an
honest result of the rules, not a bug: the final devlog goes into it.

## Verifying without a display

The dev machine has no monitor, so everything is checked headless (SDL's
dummy video driver). `main.py` grows two flags for it:

```bash
# run 420 frames, save the last one — the frame the checks analyse
SDL_VIDEODRIVER=dummy .venv/bin/python main.py --frames 420 --seed 5 --shot /tmp/frame.png
```

- the unit tests step the simulation directly (no window at all);
- `--frames` + `--shot` render real frames for pixel inspection;
- the web bundle is checked by executing the concatenated file and running
  its own loop, in both the desktop and the browser code path.

## Devlogs

Build notes, in order, in `devlog/`: foundation and first organisms, food
and reproduction, the browser build, predators and paint, the inspector,
the time machine, making the plate feel eaten, and the final pass over
predation, ecology and the interface.

# EvoLab

An interactive artificial-life simulator: virtual organisms compete for
resources, reproduce, mutate, and evolve. Watch natural selection in real
time, manipulate the environment, and run evolution experiments.

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

Controls: `Space` pauses. The header has a pause button, a speed slider,
and a mutation-rate slider. Click any organism to select it — a gold ring
tracks it and an inspector panel shows its genome as trait bars along
with its energy, age and role. Click empty space to deselect.

`R` (or the **Replay** button) rewinds into a **time machine**: the world
records a snapshot every 0.25 s, so you can scrub back through the last
~60 seconds and watch a predator–prey cycle or an extinction happen. The
speed slider controls replay speed; `Esc` (or `R`) exits back to live.

## Play in your browser

`web/` holds a browser build of the same game. PyScript runs Python
(and pygame) as WebAssembly inside the page — no server, no install,
works on any static host. The first load takes a few seconds while it
pays for Python from the CDN.

Try it locally:

```bash
cd web
python3 -m http.server 8000
# open http://localhost:8000
```

`web/evolab.py` is generated from the project sources by
`web/build.py` — re-run it after changing any module:

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
Source: Deploy from a branch**, pick `gh-pages` / `(root)`. The game
goes live at `https://YOURNAME.github.io/evolution-sim/`.

## Architecture

- `simulation/` — pure Python, no pygame: `Ecosystem` holds all state and
  only knows how to advance by `dt` seconds. The UI owns the clock.
  Organisms carry an 8-trait `Genome`; energy drains from metabolism,
  movement and body upkeep (trait tradeoffs):

  ```
  drain/s = (0.30 + 0.55·metabolism) × (1 + 0.6·speed + 0.8·size) × (1 − 0.5·efficiency)
  ```

  The plate starts pre-seeded with food and it then spawns continuously
  (capped). Food is sensed by vision — range 30–150 px depending on the
  vision trait, toroidal, re-scanned at most every 0.25 s.
  Hungry organisms steer toward the nearest food (turn rate drops with
  size) and eat on contact. They die of starvation or old age.

  Reproduction is local: a ready, energetic organism pairs with a
  ready neighbor within the mating radius. Each parent pays an energy
  cost and the two produce one baby at their midpoint. The baby's
  genome is a per-trait crossover of the parents, then a per-trait
  Gaussian mutation (probability set by the header slider). Readiness
  is gated by the fertility trait; the generation number is tracked
  and shown in the header.

  The world starts as a pure herbivore population (aggression pinned to
  zero). The `aggression` trait then drives continuous predation: each
  hungry organism hunts weaker neighbours with probability = aggression
  and forages plant food with probability (1 − aggression). Fleeing a
  stronger neighbour always outranks everything. A catch is gated on
  speed — a predator only eats prey it can actually outrun while the
  prey sprints away — so prey evolve speed to escape, predators evolve
  speed to chase, and both drift up together (the arms race). Aggression
  carries a steep upkeep surcharge and a breeding penalty, so carnivores
  stay a minority instead of wiping the plate.

  A spatial hash grid answers neighbor queries in ~O(1) per query
  regardless of population, which keeps mating and predation cheap. A
  slow stream of random immigrants remains as an extinction safety net.

  The ecosystem records a per-second history (avg speed, avg size,
  population, avg aggression), drawn as a live chart with a legend in the
  bottom-right — watch the aggression line rise as predators appear.

  For the time machine, `simulation/snapshot.py` makes cheap render-only
  copies of the world (organisms + food) on a 0.25 s cadence; the renderer
  can draw a past frame without touching the live simulation.
- `rendering/` — draws ecosystem state onto the screen (static background
  is pre-rendered, blitted every frame). Organisms are pre-rendered
  antialiased "orbs" (species colour × body radius × energy brightness)
  so the per-frame cost is one blit each: body radius = size, brightness =
  energy, heading tick length = speed, and colour sweeps green → amber →
  red as aggression rises, so selection and predation are visible on the
  plate.
- `ui/` — hand-drawn widgets (button, slider, label), the theme palette,
  and the organism `Inspector` (a selected creature's trait bars).

The simulation advances on a fixed 60 Hz timestep with an accumulator;
the speed control scales how many steps run per real second, never the
step size.

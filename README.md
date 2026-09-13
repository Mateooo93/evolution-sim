# EvoLab

EvoLab is a small artificial life simulator written in Python. Organisms move
around a 2D world, eat food, hunt each other, and breed. Each one has 8 traits
that get passed to its children with random changes, so the population slowly
changes over time while you watch.

## What happens in it

- Organisms need energy to live. Moving, having a big body, and having high
  metabolism all cost energy. If energy hits 0 they starve.
- They also age. Past a certain age (depends on the lifespan trait) they die.
- Food spawns in patches. Hungry organisms look for the closest food they can
  see and walk to it.
- Aggressive organisms hunt other organisms instead. They chase them, and if
  the prey is slower it gets caught. If the prey is faster it gets away.
- Two adults that are ready and have enough energy produce one baby. The baby's
  traits come from both parents, then each trait has a small chance to change
  a bit (mutation).

## Run it

```bash
python3 -m venv .venv
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

If `ensurepip` fails, install `python3-venv` and `python3-pip` first:

```bash
sudo apt install -y python3-venv python3-pip
```

## Controls

| Key / click | What it does |
| --- | --- |
| `Space` | pause and unpause |
| `R` | open the replay of the last minute, or close it |
| `←` `→` | move one frame while replaying |
| `Esc` | close the replay |
| click a creature | select it and show its stats in the side panel |
| click empty space | unselect |

## The header controls

| Control | Range | What it does |
| --- | --- | --- |
| FOOD | 0.1x to 2.5x | changes how fast food spawns. Low makes a famine, high makes a boom |
| AGGRESSION | -1 to 1 | pushes new babies toward hunting (positive) or eating plants (negative). 0 leaves it alone |
| SPEED | 0.25x to 20x | how many simulation steps run per real second |
| MUTATION | 0.1% to 20% | chance per trait that a baby's trait changes a bit |

The aggression slider does not force anything. It just makes it more likely
that babies go one way. If the world can't support hunters, they still die out.

## What the dots on the plate mean

| Looking at | Means |
| --- | --- |
| size of the dot | size trait |
| how bright it is | energy. Dim means nearly starving |
| length of the line sticking out | speed trait |
| colour | aggression. Green is a plant eater, red is a hunter |
| thin ring around it | it is ready to breed |
| the fading line behind it | where it has been |
| white ring and corners | the creature you selected |
| green rings | the selected creature's family |

## Play it in the browser

There is a browser version in `web/`. It runs Python with PyScript, so there is
no server and no install. The first load takes a few seconds.

```bash
cd web
python3 -m http.server 8000
# then open http://localhost:8000
```

`web/evolab.py` is built from the other files, so run the builder after you
change anything:

```bash
.venv/bin/python web/build.py
```

The live version is on the `gh-pages` branch. To update it, push the `web`
folder to that branch:

```bash
git subtree push --prefix web origin gh-pages
```

`git subtree` is not installed on every machine. If it is missing, clone the
branch somewhere and copy the two web files in by hand:

```bash
git clone -b gh-pages https://github.com/YOURNAME/evolution-sim.git site
cp web/index.html web/evolab.py site/
cd site && git add -A && git commit -m "update site" && git push
```

## Files

- `simulation/` - the world. No pygame in here, so it can run without a window.
  - `genome.py` - the 8 traits and how they turn into real numbers like speed
  - `ecosystem.py` - the rules: energy, sensing, hunting, breeding, food
  - `spatial.py` - a grid so looking for nearby creatures is fast
  - `snapshot.py` - copies of the world used by the replay
  - `types.py` - the Organism and Event data classes
- `rendering/` - draws the world onto a surface
- `ui/` - the panels, buttons, sliders and the chart
- `main.py` - sets up the window, owns the clock and the replay
- `devlog/` - notes I wrote while making it

## Numbers used in the simulation

Energy cost per second:

```
drain = (0.22 + 0.40 * metabolism) * (1 + 0.9 * speed + 0.8 * size)
        * (1 - 0.5 * efficiency) * (1 + 0.3 * aggression)
```

A few rules that matter more than the exact numbers:

- Food comes in patches of 10 items, at 9 items per second by default.
- You need to be about 5% faster than someone to chase them, and you can only
  sprint if you have more than 25% of your energy left. So a hunt usually ends
  when the one being chased runs out of energy.
- You only run away from something if it is close and faster than you.
- Hunters get less energy from plants, which is why most of the population
  still eats plants.
- If the population drops below 28, random new organisms come in slowly. This
  almost never happens once breeding is working.

On the default settings the population sits around 180 to 240 and goes up and
down on its own. Most organisms do not turn into full hunters, they stay in the
middle.

## Dev flags

```bash
SDL_VIDEODRIVER=dummy .venv/bin/python main.py --frames 420 --seed 5 --shot frame.png
```

- `--frames N` quits after N frames
- `--seed N` makes the world start the same way every run
- `--shot PATH` saves the last frame as an image

## Devlogs

`devlog/` has 8 short notes in order, from the first version up to the final
one. The last one covers the interface work and the changes I made to the
ecology after running the simulation without a window and finding out the
population was only surviving because of the random immigrants.

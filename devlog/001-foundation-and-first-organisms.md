# DevLog #1 — First Light: A Moving Ecosystem

**Date:** 2026-09-09 · **Milestones:** foundation + organisms · **Commits:** `1fdcaf7` → `24eef57`

## The idea

EvoLab is an interactive artificial-life simulator: virtual organisms
compete for resources, reproduce, mutate, and evolve, and the user watches
natural selection happen in real time. The bar I set for myself: **not a
particle toy**. A real evolutionary system where every creature carries
heritable traits, and the success of those traits reshapes the population
over time.

## The stack — a pivot

I first scaffolded the project in React + TypeScript + Vite, then decided
to move the whole thing to Python. One language for the whole project,
pygame gives me a full-screen canvas and click/mouse handling for the UI,
and Python keeps the door open for proper numeric tooling when I start
analyzing population statistics. I went with **pygame-ce** — the actively
maintained fork of pygame — because the original no longer ships wheels
for Python 3.13.

## Architecture: the sim never knows the UI exists

The single most important rule I set for myself: the simulation must not
know the UI exists.

```
simulation/   pure Python, no pygame. Ecosystem only knows how to advance
              by dt seconds. The UI owns the clock.
rendering/    a dumb view — reads simulation state, paints it.
ui/           hand-drawn widgets (button, slider, label) + theme palette.
```

Why: everything I want later — statistics graphs, creature inspection,
save/share, experiments — is easier when the world can run headless
without a window.

Two decisions on the game loop:

- **Fixed timestep with an accumulator.** The game logic always advances
  in 1/60 s steps. The speed slider scales *how many* steps run per real
  second, never the *size* of a step — so behavior is identical at 0.25×
  and 20×, just faster or slower. `dt` is clamped (0.25 s) and catch-up
  is capped (32 steps/frame), so a stalled window can never teleport the
  world into the future.
- **Toroidal world.** Edges wrap instead of bouncing. No boundary cases,
  and the population behaves identically everywhere.

## Organisms: traits with a price tag

Every creature carries an 8-trait genome, all floats in [0, 1]:
speed, size, vision, metabolism, fertility, lifespan, aggression,
efficiency. Vision/fertility/aggression are dormant for now — they light
up in later milestones.

The energy model is where the tradeoffs live:

```
drain/s = (0.10 + 0.40·metabolism) × (1 + 0.6·speed + 0.8·size) × (1 − 0.5·efficiency)
```

A slow, small, efficient body burns ~0.05 energy/s (tens of minutes of
life); a maxed-out fast, big, high-metabolism body burns ~1.2/s (~80
seconds). Death is either **starvation** (energy hits 0) or **old age**
(age exceeds lifespan, 120–600 s depending on the trait).

**The immigration floor (temporary):** with no food yet, energy only ever
drains, so eventually everyone dies and the plate empties. While the
population is below 40, one fresh random immigrant spawns per second.
It's an honest placeholder for real births — the food milestone replaces
it.

## Making evolution visible

The goal I set for myself: selection should be **visible without reading a
chart**.

- body radius = size
- body brightness = energy (dim = starving, bright = healthy)
- heading tick length = speed

Run it at 1× for two minutes and you can watch the fast, big,
high-metabolism creatures dim first. That's natural selection, visible on
sight. The header also reports population and average speed/size, which
drift as the unfit die out.

## Testing without a display

The dev machine has no monitor, so verification runs headless (SDL's
dummy video driver):

- run the simulation for 900 simulated seconds: all 100 original
  organisms die (starvation + age counters exact), and immigration holds
  the population at exactly the floor.
- render to an offscreen surface and sample pixels: a full-energy
  max-size body is the exact accent green; a starved one is the exact
  dimmed color.
- boot the actual app for a few hundred frames and confirm a clean exit.

## What's next

**Food.** Spawning, sensing — this is where the dormant *vision* trait
comes alive — and eating. After that: reproduction with crossover and
mutation, the moment the gene pool actually starts to change.

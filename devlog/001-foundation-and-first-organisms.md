# DevLog #1 first organisms

started this on the 9th. the idea is a small ecosystem where the creatures
evolve, not a particle toy that just looks busy. every creature carries eight
traits and passes them on, so what survives changes the population.

i first built it in react and vite because that is what i knew, then threw that
away and moved to python. one language for the whole project, pygame gives me a
window and mouse handling, and python leaves the door open for doing stats
later. i used pygame-ce because plain pygame has no wheels for python 3.13.

the rule i kept: the simulation must not know the ui exists.

  simulation/  no pygame, has the world, only knows how to advance by dt
  rendering/   reads the world and draws it
  ui/          buttons, sliders, colours

that way i can run the world with no window at all.

the loop is a fixed timestep with an accumulator. physics steps are always
1/60th of a second and the speed slider changes how many steps run per second,
so 0.25x and 20x behave the same, just slower or faster. dt is clamped to a
quarter second and catch up is capped at 32 steps, so dragging the window
around does not teleport the world into the future.

the world wraps at the edges instead of having walls, which got rid of a lot of
edge cases.

eight traits, all floats between 0 and 1: speed, size, vision, metabolism,
fertility, lifespan, aggression, efficiency. only some of them did anything at
this point.

energy is where the tradeoffs are. it drains per second as metabolism times
body and movement upkeep, minus whatever efficiency saves. a slow small
efficient creature burns about 0.05 a second and lives for ages. a fast big one
with high metabolism burns about 1.2 and dies in a minute and a half. you die
by starving or by getting old.

with no food yet, energy only ever goes down, so everybody dies eventually and
the plate empties. while the population is under 40 i spawn one random new
creature per second. that is a placeholder until food exists.

i wanted selection to be visible without reading a chart, so the body radius is
the size trait, brightness is energy and the little line is speed and heading.
run it for two minutes at 1x and you can watch the fast big ones go dim first.

the machine i am on has no monitor, so everything is tested headless with SDL's
dummy video driver. 900 simulated seconds: all 100 original creatures die,
starvation and age counters line up exactly, and the population sits on the
immigration floor. render to an offscreen surface and sample pixels: a
full-energy max-size body is the accent green, a starved one is the dim colour.

next: food.

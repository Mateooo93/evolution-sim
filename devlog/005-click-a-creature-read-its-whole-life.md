DevLog #5 click a creature, read its whole life

you can click creatures now. click any of the little things on the plate
and it gets a gold ring around it that follows it around, and a panel
pops up in the corner that tells you everything about it: its id, its
generation, whether it is a hunter or a grazer, how much energy it has,
how old it is, and all eight of its genome traits drawn as little bars.

the genome, finally visible
the game has been carrying around these eight hidden traits since the
first organisms - speed, size, vision, metabolism, fertility, lifespan,
aggression, efficiency - and now you can actually look at them on one
living creature. its the difference between watching a blob wander and
knowing that specific blob has maxed-out speed but is burning itself
alive on metabolism. you click the fastest one on the plate and see
exactly why it needs to eat every two seconds. clicking a red one shows
you the aggression that makes it a hunter at a glance.

click to track, click off
clicking empty space deselects. if your favourite creature dies, the
selection just clears itself instead of hanging around pointing at
nothing. and the panel follows the creature as it swims, so you can watch
it try to catch food or run from a predator with its numbers ticking
underneath.

the lab chart got real
the little sparklines in the corner are now a proper chart with a legend:
population, average speed, and average aggression all plotted over the
last few minutes. the aggression line is the new one and its great,
because you literally watch it climb as predators start showing up across
the plate. the speed line is the arms race in real time. i also added the
average aggression number to the readout in the header bar.

this one was mostly plumbing honestly - hit testing to figure out which
creature you clicked, a selection ring that has to draw on top of
everything, and a panel that reads a genome and paints eight bars. no
crazy simulation changes, just making the organisms inspectable, which
turns out to be the most fun part of the whole sim.

NEXT
next im gonna let you rewind. keep the last couple minutes of the whole
world in a ring buffer and scrub back through it, so you can watch a
predator-prey cycle happen or see exactly when a species went extinct.
basically a time machine for the plate.
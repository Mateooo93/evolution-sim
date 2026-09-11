DevLog #2 Food and reproduction

The ecosystem now has a full food loop: creatures sense food, chase it,
eat it, and breed. Eat, survive, reproduce, die - and with every
generation the gene pool shifts a little.

food
food spawns continuously but it is capped, because the world is finite
and the plate should run out when a population gets too big. Creatures
sense food with their vision trait - range 30 to 150 px - on the wrapped
world, and they only re-scan when they are hungry and their target is
stale, so a starving population cant waste cycles scanning every tick.
Hungry ones steer toward the nearest food and the turn rate drops with
size, so big creatures are clumsy hunters. Eating is contact: touch the
food, gain the energy.

The first version had a problem I only noticed after watching it run:
nothing looked like it was happening. Every creature spawned full, so
the first 40 seconds were pure wandering while food just piled up, and
the food was the same green as the creatures, so the eating was
invisible. The fix: the world now starts pre-seeded with food,
creatures spawn partially hungry so the hunting begins at t=0, and the
food is amber so you can actually watch it get eaten.

reproduction
Mating is local: a ready creature only breeds with a ready neighbor
inside a small mating radius, so the gene pool picks up spatial
structure instead of any-two-random mixing. Both parents pay an energy
cost and the baby spawns at their midpoint with a genome that is a
per-trait crossover of the two parents, followed by a gaussian nudge on
each trait with the probability set by the new mutation slider in the
header (0.1% to 20%). The fertility trait controls how fast readiness
builds up, so lazy genomes breed slower, and generations are tracked per
creature with the highest one alive shown in the header.

Finding a partner is a neighbor query, so I added a spatial hash grid:
rebuilt every tick, and a query only touches the cells a circle
overlaps, so it stays cheap no matter how big the population gets.
Predators will run on the same grid. There is also a little sparkline
panel in the bottom-right now (population and average speed over time) -
the first step toward the real stats milestone.

NEXT
next im gonna make predators! the aggression trait finally gets used -
hunters that chase the slow, and prey that learn to run. and i want to
tune the world until the evolution is obvious in the sparklines, speed
and size drifting on their own!

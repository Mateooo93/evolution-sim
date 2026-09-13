# DevLog #2 food and reproduction

the food loop works now. creatures sense food, walk to it, eat it, and breed.
eat, survive, breed, die, and the gene pool moves a bit every generation.

food spawns continuously but the plate has a cap, because the world is finite
and it should run out when the population gets too big. creatures find food
with their vision trait, which is 30 to 150 pixels depending on the genome, and
distances wrap around the edges. they only rescan when they are hungry and
their current target is gone, so nobody is scanning every tick. the turn rate
drops with size, so big creatures are clumsy.

eating is just contact. touch it, gain the energy.

the first version had a problem i only saw after watching it for a while:
nothing looked like it was happening. everybody spawned full, so the first 40
seconds were wandering while food piled up, and the food was the same green as
the creatures so you could not tell it was being eaten. fixed by starting the
plate with food on it, spawning creatures a bit hungry so they hunt from the
start, and making the food amber.

breeding is local. two creatures that are ready and can afford it produce one
baby at the midpoint. the genome is a per-trait crossover of the parents, then
each trait has a chance to get a small nudge, and that chance is the mutation
slider in the header (0.1% to 20%). the fertility trait decides how fast a
creature gets ready, so lazy genomes breed slower. generations are tracked and
the highest one alive shows in the header.

finding a partner is a neighbour query, so i added a spatial hash grid. it gets
rebuilt every tick and a query only touches the cells a circle overlaps, which
keeps it cheap as the population grows. predators will use the same one.

there is also a small graph in the corner now with population and average speed
over time.

next: the aggression trait, which has been sitting there doing nothing.

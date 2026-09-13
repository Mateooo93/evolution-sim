# DevLog #5 clicking a creature

you can click creatures now. click one and it gets a ring around it that
follows it around the plate, and a panel in the corner shows its id, its
generation, whether it is a hunter or a plant eater, its energy, its age, and
all eight genome traits as bars.

the eight traits have been sitting in the background since the first version,
so seeing them on one creature is the good part. you click the fastest thing on
the plate and find out it is fast because its metabolism is maxed and it has to
eat constantly to stay alive. you click a red one and see the aggression number
that makes it a hunter.

clicking empty space deselects. if your creature dies the selection clears by
itself instead of pointing at nothing. the ring follows it around while it
swims, so you can watch it chase food or run from something with the numbers
updating underneath.

the graph in the corner has a legend now. population, average speed and
average aggression over the last few minutes. the aggression line is the one i
wanted, because it climbs as hunters spread. average aggression is in the
header too.

most of this was plumbing. working out which creature you clicked, drawing the
selection ring on top of everything else, and reading one genome to paint eight
bars. no simulation changes at all, and it is the most fun part of the project
so far.

next: rewinding. i want to keep the last couple of minutes of the world and
scrub back through it.

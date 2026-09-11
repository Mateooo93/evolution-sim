DevLog #4 predators and the pretty paint

Predators are in, and the whole plate got a makeover. creatures now split
into hunters and prey, they chase each other across the sea, and on top
of that the game looks way less like a science fair scatter plot and more
like something youd want to watch for an hour.

predators
the aggression trait finally does something. every hungry creature makes
a little gamble each time it gets hungry: with probability aggression it
goes hunting, otherwise it keeps grazing plants. so a pure herbivore
never hunts, a full carnivore almost always does, and everything in
between is an opportunist that does a bit of both. theres no clean
"this one is a predator, this one is prey" label anymore, its a whole
spectrum, and the color shows it: green for the peaceful grazers, shifting
through amber and into red for the dangerous ones.

the fun part is that catching is a speed race, not a given. a hunter can
only eat prey it can genuinely outrun while the prey sprints away with a
fear response. so prey evolve to be faster to get away, and predators
evolve to be faster to keep up, and you can watch both drift upward in
the sparklines over time. that is the arms race and it finally gives the
speed trait a real reason to exist instead of just being a bit of a
tax on your metabolism.

the hard part
this took a lot longer than the food system. my first attempt was a hard
cutoff: aggression above a threshold meant predator, below meant prey.
and it just collapsed. the population would eat itself down to a little
hollow pack of hyper-carnivores in under two minutes, every single time,
in every balance i tried. what finally fixed it was making aggression a
continuum with real costs - steep upkeep, a breeding penalty - and
gating the catch on literally outrunning the prey, so one freak killer
could no longer clear the whole plate by himself. the smarter speed-gate
was the turnaround.

i also hit a sneaky bug that was driving all my tuning math insane: for
a while the creatures were starving to death on a plate completely
covered in food. zero food items ever eaten. turned out the sense timer
that should throttle the food scan was being refreshed every frame by the
hunting logic, so they never actually re-looked for food. fixing that one
line changed everything - suddenly the world works like a real ecosystem.

pretty paint
the old flat color dots are gone. every creature is now a soft glowing
orb with a bright core and a little halo, pre-rendered once so the
expensive antialiasing is free at runtime - it still runs at 60fps
with a couple hundred on screen. the color gradient across the aggression
trait is the big one though, because now you can literally watch
predators appear as the plate goes from all green to dotted with red.

NEXT
next im gonna make a proper sidebar so you can click a creature and see
its whole genome and family tree, and plot the real stats over time -
population, average aggression, how the speed arms race is going. basically
turn the sparklines into a full lab dashboard. and i want to tune the
world until the predator-prey cycles show up as heartbeat waves in the
graphs, not just noise.
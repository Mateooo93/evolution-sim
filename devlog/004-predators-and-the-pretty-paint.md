# DevLog #4 predators

predators are in. aggression is a spectrum, not on or off. when a creature is
hungry it rolls against its aggression: hunt a weaker neighbour, or keep eating
plants. a pure plant eater never hunts, a full hunter almost always does, and
everything in the middle does a bit of both.

the catch is a speed contest. you can only eat prey you can actually outrun
while the prey is sprinting away, so if it is faster it gets away. prey that
are fast live longer, predators that are fast eat, and both traits creep up
over a few minutes. that is the arms race, and it is the first thing that gives
the speed trait a reason to exist other than costing you energy.

this took much longer than the food did. the first version used a hard cutoff
for aggression and the population turned into all carnivores in about two
minutes, every time, whatever i did to the numbers. making it a continuous
trait with real costs and gating the catch on speed is what made it work.

there was also a bug where creatures starved to death on a plate covered in
food. the hunting code was overwriting the timer that food scanning uses, so
once they decided to hunt they never looked for food again. one line.

and they glow now. the flat dots are gone. they are soft round cells that go
green to amber to red as aggression goes up, so you can see the plate change
colour as hunters show up.

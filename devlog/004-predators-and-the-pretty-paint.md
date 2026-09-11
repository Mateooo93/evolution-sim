DevLog #4 predators and the pretty paint

Predators are in. Aggression is now a spectrum instead of a simple on or
off: every hungry creature makes a little gamble - hunt weaker neighbours
with probability equal to its aggression, or keep grazing plants. a pure
herbivore never hunts, a full carnivore almost always does, and everything
in between is an opportunist that does a bit of both.

the fun part is the catch. you can only eat prey you can actually outrun
while the prey sprints away, so it is a real speed race. prey evolve to
run faster to escape, predators evolve to keep up, and you can watch both
drift up in the sparklines over time. that is the arms race and it finally
gives the speed trait a reason to exist instead of just taxing your
metabolism.

it took way longer than the food system. my first version was a hard
cutoff and it collapsed the whole population into hyper-carnivores in
under two minutes every single time, no matter how i balanced it. making
aggression a continuum with real costs and gating the catch on outrunning
prey is what finally made it work. there was also a sneaky bug where the
creatures were starving to death on a plate completely covered in food,
because the hunting logic was stomping the food-scan timer - one fixed
line and it became a real ecosystem.

and everything glows now. the old flat dots are gone, replaced by soft
antialiased cells that go green to amber to red as they get dangerous,
so you can literally watch predators appear as the plate changes colour.
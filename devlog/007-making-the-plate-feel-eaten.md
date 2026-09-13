# DevLog #7 making the plate feel eaten

two small changes did a lot for how the game feels. food used to sit at the cap
forever because spawning kept up with whatever the population ate, so the amber
dots never went away and you never got to watch one get eaten. so i flipped it
around. food spawns slower than the population eats now, and the cap is lower.
the plate clears in patches and refills, creatures actually have to travel to
find a meal, and when a batch of births lands it can strip the field in
seconds.

the other one is the eat pulse. every time a food item disappears an expanding
ring of light comes out of that spot for a third of a second, warm amber,
fading as it grows. it is a small thing but it changes how you read the plate.
a creature touches a dot, the dot vanishes, a ring goes out, and you know that
one got it. eating goes from something you miss to the most obvious thing on
the screen. i detect it by comparing the food positions between frames, so it
is pure drawing and the simulation does not know it exists.

between the tails from last time and the pulses now, most of what you want to
know is visible without clicking anything. green tails heading for food, red
tails heading for green ones, amber rings where meals happened. you can watch
it like a fish tank and follow one creature by its tail.

the tradeoff is that the world is harsher. more starvation, smaller booms,
tighter runs. the population can still climb to sixty-something and clear the
field down to a handful of dots, then breed back up. that up and down is what i
wanted the chart to show.

next: tune the food until the population cycle is a clean wave instead of
noise, then track family lines.

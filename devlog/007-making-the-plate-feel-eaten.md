DevLog #7 making the plate feel eaten

two small changes did a huge amount for how the game feels. food was
sitting around at the cap forever - spawn kept up with whatever the
population ate, so the amber dots never actually went away and you never
got the little dopamine hit of watching a thing get consumed. so i flipped
the balance: food now spawns slower than the population eats, and the
cap is lower. now the plate visibly clears in patches and refills, hungry
creatures have to actually travel to find a meal, and when a wave of
births hits it can strip the field in seconds.

the pulse
the satisfying part is the eat pulse. each time a food item disappears an
expanding ring of light blooms out from the spot for a third of a second,
warm amber, fading as it grows. its a tiny thing but it completely changes
the read: you see a creature touch a dot, the dot vanishes and sends out a
little ripple, and you instinctively know that one got it. eating goes
from something youd miss to the most legible event on the plate. i
detect it by diffing the food positions between frames - anything that
was there a frame ago and isnt now was eaten - so its pure render, the
simulation doesnt even know the pulse exists.

why it matters
between the movement trails from last time and the eat pulse now, almost
everything youd want to know about the world is visible before you
reason about it. green tails hunting, red tails hunting them, amber
ripples where meals landed. you can sit and watch it like an aquarium and
follow individual creatures by their tail without clicking a single one.

the tradeoff
making food scarce does mean harsher survival - more starvation, smaller
swings up in population, some runs end up tense and tight. i kept the
numbers so the world always pulls through (predators stay a minority,
prey keep the plate from emptying forever) but it definitely runs
leaner than it did. a population can still boom to sixty-some and clear
the field to a handful of dots, then the survivors breed it back. that
up-and-down is exactly the rhythm i was hoping the chart would show.

NEXT
next im gonna keep pushing on that rhythm - tune the food economy until
predator-prey cycles show up as clean heartbeat waves in the pop chart,
not noise. and then lineage tracking: click a creature and find every
living descendant of its great-great-grandparent, and watch a family
line either take over the plate or quietly die out.
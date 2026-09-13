# DevLog #8 last one

this one is about the interface and about the thing the interface made me
find.

the plate used to be the whole window with a row of numbers on top. now it has
a frame and the readouts have a column down the right side: population, food,
generation, births, deaths, a graph of the last five minutes, a list of recent
events, and the creature you clicked. the panel for a clicked creature shows
the eight traits as bars with a tick on each bar marking the population
average, so you can tell if that creature is fast for its time. clicking one
also puts a dim ring on every living member of its family, which is how you
find out whether a family is taking over or dying out.

then i ran the world for 900 seconds with no window and printed the totals, and
found out the project was fake. 231 immigrants. the population was sitting on
the immigration floor, which means the ecosystem could not feed itself and was
being kept alive by random new creatures arriving. three numbers explained it.
27 energy per second coming in against a population burning over 100. 86% of
hunts finding nothing to chase. 481,000 fleeing ticks against 174,000 steering
ticks, so they spent most of their lives running away from each other, and
running costs energy.

what i changed: food arrives in patches instead of single dots (with single
dots, speed won every race, everybody hit max speed, and then nothing could
ever catch anything), sprinting needs energy so a chase can be won by outlasting
the other one, you only run if the thing chasing you is close and faster, and
the cost moved off the aggression gene and onto the chase itself. taxing the
gene meant no mutant could ever afford the middle of the range.

900 seconds from 90 creatures now: population 182 to 245, no immigrants, 117
hunts, 1216 births, generation 27.

i did not get a proper predator species. aggression settles around 0.05 to 0.22
and stays in one lump, so there are hunters but no separate red kind of
creature. hunting gets less worth doing the more of you are doing it, so it
settles in the middle. i left it as it is instead of tuning it until the graph
looked like the story i wanted. it probably needs prey refuges or a handling
time before you can eat something.

i also gave the player the two knobs i had been turning by hand all week. FOOD
scales the supply. AGGRESSION pulls every newborn 40% of the way toward hunter
or toward grazer, on top of whatever it inherited. if you wind aggression to
+1 you do not get a plate of killers, you get a plate where everybody is the
same and nobody can hunt anybody, because hunting needs you to be 0.1 more
aggressive than the other one. zero kills, population down to a third, food
piling up. good demo of why hunters stay rare.

last thing: the trails were 70% of every frame, because each one was drawn as
about ten blended line segments. drawing them as two lines instead took the
frame from 16.7ms to 5.8ms.

eight devlogs, three layers that do not know about each other, and a plate that
runs itself now. the drawing code always worked on the first or second try. the
ecology took a stopwatch and about twenty experiments to stop lying to me. if
you build one of these, run the world with no window and print the totals
before you write a single button.

# DevLog #6 the time machine

you can rewind the plate now. press R and a bar slides out under the header
with a slider on it. drag it anywhere in the last minute and the world jumps to
that moment. you can freeze a chase halfway through, or go back and find the
second a family died out and see what the numbers were doing before it.

how it works: the world was already a separate simulation, so this is just
copies. every quarter of a second the game copies every creature and every bit
of food into a list, and keeps the last 240 of those, which is about a minute.
the slider is a position in that list. copying is cheap because a creature is
just a position, a genome and an energy number. the pointers like "what am i
chasing right now" get dropped, since they mean nothing in a stored frame.

what i changed on the plate: creatures leave a short fading tail behind them
now, tinted by their own aggression, so the plate has movement in it and you
can see a hunt as a streak before the two dots touch. there is also a vignette
on the background so the empty space looks like depth instead of flat black.
neither of those touches the simulation, it is all in the drawing code.

the tails are what changed the feel the most. a pale yellow tail pointing at
food tells you what a creature wants before it gets there, and a red tail
moving against a plate of green ones is a hunter you can spot from across the
screen.

next: tuning predator and prey numbers so the population graph does something
other than wobble, then family lines.

DevLog #6 the time machine

you can rewind the whole plate now. hit R (or the Replay button) and it
flips back into the last sixty seconds, scrubbing through the world a few
frames at a time while a replay bar counts along. watch a predator actually
pounce, or rewind to the exact second a whole lineage went extinct and see
why it died. press R or Esc and it drops you back to live, right where you
left off.

how it works
the world was already a pure simulation, so the time machine is just
snapshots. every quarter second the game copies the entire world - every
organism's position, genome, energy, plus all the food - and keeps only
the last 240 of those frames in a ring, which is about a minute of
history. when you hit R it stops simulating and just plays those frames
back. the copy is light because each organism only needs its traits and
where it is; the "who am i chasing right now" pointers that only matter in
live time get dropped, so a stored frame is tiny.

the speed slider is the scrubber. crank it up and the replay fast-forwards
through the extinction, drop it down and you watch one creature's last
few steps frame by frame. the arrow keys jump a single frame at a time if
you want to be surgical.

why i built it
the simulator already shows you a population fighting to survive, but you
only ever saw the present. a predator-prey cycle takes a couple minutes -
if you blinked you missed it. rewinding is how you actually understand
what happened instead of just that something did. its also just satisfying
to rewind twenty seconds to the exact frame a red dot caught a green one
and watch it from the other angle.

this one was mostly plumbing too, which is the theme of these last
couple devlogs - making things inspectable and reviewable turns a neat
demo into a tool you can learn from.

NEXT
next im gonna tune the world so predator-prey cycles actually show up as
clean heartbeat waves in the chart, instead of noisy blobs. that means
watching tradeoffs between prey birth rate, hunter upkeep and catch speed
until the population graph breathes. then maybe lineage tracking - click
a creature and see the whole family tree back to its great-great-
grandparent.
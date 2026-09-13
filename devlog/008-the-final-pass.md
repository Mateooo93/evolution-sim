# DevLog #8 — last one

**Date:** 2026-09-13

## the interface

the plate used to be the whole window with a cramped row of numbers on
top. now it has a frame and everything else has a home: a header with the
controls grouped, a legend bar naming every colour, and a sidebar with
four panels — ecosystem (pop, food, generation, births, deaths, and a bar
splitting grazers / mixed / hunters), trends, recent (an event log), and
selected.

selected is my favourite bit. it draws the creature the way the plate
does, then its family line, then all 8 traits as bars with a tick on each
bar showing the POPULATION average. the bars used to tell you a number;
now they tell you if this thing is fast for its time. clicking also rings
the creatures living family on the plate, so you can watch one line take
the plate over or die out.

## the part where i found out the sim was fake

i ran the world headless for 900 seconds and printed the totals. 231
immigrants. the population was parked on the immigration floor, which
means the ecosystem could not feed itself and was being kept alive by a
drip of random strangers. not evolution, a bug with a story written round
it. three numbers:

- 27 energy/sec coming in against a population burning 100+. the world
  was bankrupt.
- 86% of hunts found nothing to chase, and the ones that did were paying
  3.5x a grazers metabolism for the privilege.
- 481,000 flee ticks vs 174,000 steering ticks. they spent their lives
  sprinting away from each other, and panic costs energy, so the sim was
  selecting AGAINST being prey.

the fixes: food comes in patches now (with even food, speed was a runaway
scramble trait — everyone hit max speed and then nothing could catch
anything); sprinting costs energy so a chase is an endurance chase; panic
only when the threat is close AND faster; the cost moved off the gene and
onto the chase, because taxing the trait dug a valley no mutant could
climb out of; and meals got small and frequent so the plate reads as
grazed.

900s unattended from 90 founders now: population 182-245, zero
immigrants, 117 hunts, 1216 births, deepest generation 27.

## what i couldnt get

a predator caste. aggression settles at 0.05-0.22 in one lump, so there is
no separate red ecotype, just a grazer majority with a hunting tail. the
hunts are real, they just never become a *role* — hunting gets less
profitable the more of you do it, so it settles in the middle instead of
splitting in two. i left it honest rather than tuning until the picture
matched the story i wanted.

## the two dials

FOOD scales the supply live. AGGRESSION pulls every newborn 40% of the way
toward hunter (or grazer if negative) — a bias on inheritance, not a
cheat, you push and selection pushes back. winding it to +1 does not give
you a plate of killers: everyone lands at the same aggression, nobody is
0.1 more aggressive than anyone else, so nobody can hunt at all. zero
kills, population down to a third, food piling up under a plate of
starving red dots. better demo of why predators stay rare than anything i
could have designed.

## the end

eight devlogs, three layers that dont know about each other, a browser
build, and a plate that finally runs itself. the graphics were never the
hard part — every visual idea worked first or second try. the ecology took
a stopwatch and twenty experiments to stop lying to me. if you build one
of these: run the world headless and print the totals before you write a
single button.

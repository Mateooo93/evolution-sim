# DevLog #8 — The Final Pass

**Date:** 2026-09-13 · **Scope:** the interface, the ecology, the ending

this is the last one. i set out to make the interface carry the story
better, and then to make the world worth watching at all, and the second
half turned out to be the real work. the passing-the-time version of this
devlog would be about buttons. the honest version is that i pointed a
stopwatch at my own simulation and found out it had been on life support
for weeks.

## the interface gets a floor plan

the plate used to be the whole window with a cramped row of readouts
floating over it. now the plate is a real region with a frame around it,
and everything else has a home: a header with the controls grouped and
labelled, a legend bar that names every colour and ring on the plate, and
a sidebar with four panels. ecosystem (population, food, generation,
births, deaths, and a bar showing how the plate splits between grazers,
mixed feeders and hunters), trends (population, food and mean aggression
over the last five minutes), recent (an event log — kills logged as they
happen with both ids, everything else summarised once a second), and
selected.

the specimen panel is the part i actually care about. it draws the
creature the way the plate draws it, then its role, its family line,
energy / age / readiness meters, and all eight traits as bars — with a
tick on each bar marking the *population average*. that tick is the whole
point. before, the trait bars told you a number; now they answer the only
question worth asking about a genome, which is whether it is ahead of its
time or behind it.

the plate got the other half of the same idea. clicking a creature puts
white corner brackets on it and lights up every living member of its
family line with a dim ring, so you can watch one family either take over
the plate or quietly die out. eat pulses stayed from last time and
predation got its own red pulse, so a kill reads as a kill and not a
disappearing dot.

## the lineage thing i promised last devlog

every organism now carries its parents' ids and the id of the founder its
line descends from. that is about fifteen lines of bookkeeping in the
simulation and it buys two numbers in the panel: how many of this line are
alive right now (and what share of the plate that is), and how many living
descendants this specific creature has. the first one is the interesting
one — a line at 3% is a doomed family and a line at 60% is the plate.

## the part that was actually broken

i ran the world headless for nine hundred simulated seconds and printed
the totals. two hundred and thirty-one immigrants. the population was
sitting on the immigration floor, meaning the ecosystem could not feed
itself and was being propped up by a drip of random strangers — who,
being random, also had a mean aggression of 0.5 and were quietly poisoning
the gene pool. that is not evolution, that is a bug with a story written
around it.

so i instrumented it and found three things:

- **the energy budget was negative.** food was arriving as roughly 27
  energy per second against a population that burned over a hundred. no
  amount of clever behaviour survives arithmetic.
- **86% of hunts found nothing catchable**, and the hunters that did chase
  were paying up to 3.5x a grazer's metabolism for the privilege of
  carrying the gene. predation was a fitness trap, not a niche.
- **everyone was panicking.** 481,000 flee ticks against 174,000 steering
  ticks: creatures spent more of their lives sprinting away from
  neighbours than doing anything else. panic costs energy, so the world
  was selecting *against* being prey.

the fixes are the most interesting code in the project now:

- **food arrives in patches.** scattered uniformly, food made speed a
  runaway scramble trait — every meal was a lone dot, so the fastest
  creature won every race, and within ten minutes the whole population sat
  at maximum speed. which meant nobody could outrun anybody, which meant
  predation could never work. with meadows, a forager that finds one eats
  several meals without travelling, speed stops being the only thing that
  matters, and prey gather exactly where a hunter knows to look.
- **sprinting needs energy.** a chase is now an endurance chase: prey
  only panic at a threat that is close and genuinely faster, and a sprint
  costs energy they may not have. a fresh, alert prey escapes a hunter of
  similar speed; a tired one doesn't.
- **you pay for hunting, not for the gene.** the chase burns extra energy
  and an unused aggression gene is nearly free, so a mutant that hunts a
  little pays a little. the old version taxed the trait, which dug a
  valley no intermediate could cross — aggression could never climb.
- **meals got small and frequent.** the same energy flow as fewer, bigger
  items leaves the plate visibly grazed instead of stripped bare.

the result, over ten minutes, unattended, seeded once from ninety
founders: population 182–245, **zero immigrants**, 117 successful hunts,
1,216 births, and the deepest generation at 27. selection visibly pushes
speed up and body size down on the trends chart. the safety net never
fires.

## what i did not get

a predator caste. mean aggression settles low (0.05–0.22 depending on the
run) and the distribution stays unimodal — no separate red-blooded
ecotype, just a grazer majority with a hunting tail. the hunts are real
(hundreds per ten minutes) but they never become a *role*. i know roughly
why: as aggression rises, the pool of prey weaker than you by the
required margin shrinks, so hunting is frequency-dependent and settles at
an interior optimum instead of splitting the population in two. the
things i would try next are a handling time before you can swallow a kill,
refuges that let prey hold a patch, or a swallow rule that ties body size
to what you can eat. i left it honest rather than tuned until the picture
looked like the story i wanted.

## the frame budget

the movement trails were 70% of every frame — 1,500 individual
alpha-blended line segments. drawing each tail as two polylines (dim tail,
bright leading edge) instead of one blended line per segment took the
render from 16.7 ms to 5.8 ms, which is the difference between a
simulation that can run at 60 fps and one that cannot. same picture, a
tenth of the cost.

| | before | after |
| --- | --- | --- |
| population (400 s, same seed and start) | 29–43, pinned at the immigration floor | 119–268, mean 187 |
| immigrants | 231 | 0 |
| successful hunts | 38 | 96 |
| mean speed | drifting to the ceiling, unopposed | the same, but now it costs something |
| render (plate only) | 16.7 ms | 5.8 ms |

## the ending

eight devlogs, three layers that don't know about each other, one browser
build, a test suite, and a plate that now runs itself. the thing i did not
expect: the graphics were never the hard part. every visual idea worked on
the first or second try, and the ecology took a stopwatch, a pile of
instrumentation and about twenty experiments to stop lying to me. the
lesson i would hand to anyone starting the same project is embarrassingly
simple — run the world headless, print the totals, and do that before you
write a single widget.

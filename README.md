EvoLab
======

EvoLab is a small artificial life simulator I made in Python with pygame. It
puts a few hundred organisms on a 2D world and lets them get on with it. They
walk around, eat food, run away from each other, hunt each other, and breed.
Every organism has 8 traits and passes them to its kids with small random
changes, so over a few minutes the population changes on its own and you can
watch that happen.

To run it you need Python 3 and pygame. Make a virtual environment, install the
requirements, then start it:

    python3 -m venv .venv
    .venv/bin/python -m ensurepip --upgrade
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python main.py

If ensurepip fails you are missing the venv package, so run "sudo apt install
python3-venv python3-pip" first.

The controls are space to pause, R to open the replay of the last minute, the
left and right arrow keys to step through it, escape to close it, and clicking
on a creature selects it and shows its stats in the side panel. Clicking empty
space unselects it.

In the header there are four sliders. FOOD changes how fast food spawns, from
0.1x up to 2.5x, so you can starve the world or make it boom. AGGRESSION goes
from -1 to 1 and pushes new babies toward hunting or toward eating plants. It
does not force anything, it just makes one direction more likely, so if the
world can't feed hunters they still die out. SPEED is how many simulation steps
run per second and goes up to 20x, and MUTATION is the chance that a baby's
trait changes a bit, from 0.1% to 20%.

The dots on the plate tell you what is going on without clicking anything. The
size of a dot is its size trait, how bright it is is its energy so a dim one is
nearly starving, the little line sticking out shows which way it is facing and
how fast it is, and the colour is aggression, green for a plant eater and red
for a hunter. A thin ring means it is ready to breed. The fading line behind it
is where it has been, and since that is tinted the same way you can see a hunt
as a red tail chasing a green one. When you select something it gets a white
ring and corner brackets, and every living member of its family line gets a dim
green ring, which is how you find out whether a family is taking over the plate
or dying out.

The side panel has four parts. The first one shows the population, how much
food is on the plate, the deepest generation, births and deaths, and a bar
splitting the population into plant eaters, mixed and hunters. The second is a
chart of population, food and mean aggression over the last five minutes, with
each line scaled to its own range so you are looking at the shape rather than
the numbers, and the current values printed underneath it. The third is a log:
kills appear as they happen and everything else is added up once per second. The
fourth is the creature you selected. It shows it drawn the same way the plate
draws it, its role, its family line, how many living descendants it has, meters
for energy, age and how ready it is to breed, and all 8 traits as bars. Each bar
has a tick on it showing the population average, so you can tell if that
creature is fast for its time or not.

The world itself is in simulation/ and has no pygame in it at all, so it can
run without a window. genome.py has the 8 traits and the code that turns them
into real numbers like speed in pixels per second. ecosystem.py has the rules,
which is energy, sensing, hunting, breeding and food. spatial.py is a grid so
that finding nearby creatures does not mean checking all of them, and there is
a second grid just for food. snapshot.py makes copies of the world for the
replay, and types.py has the Organism and Event classes. rendering/ draws the
world and ui/ has the panels, buttons, sliders and the chart. main.py sets up
the window and owns the clock and the replay.

Energy is the main thing in the simulation, and it costs this much per second:

    drain = (0.22 + 0.40 * metabolism) * (1 + 0.9 * speed + 0.8 * size)
            * (1 - 0.5 * efficiency) * (1 + 0.3 * aggression)

Some rules matter more than the exact numbers. Food arrives in patches of 10
items, at 9 items a second by default. To chase something you need to be about
5% faster than it, and you can only sprint if you have more than 25% of your
energy left, so a hunt usually ends when the one being chased runs out of
energy. You only run away from something if it is close and faster than you,
because otherwise running just wastes energy. Hunters get less energy out of
plants, which is why most of the population stays plant eaters. If the
population somehow drops below 28, random new organisms start coming in slowly,
but that almost never happens once breeding is working. On the normal settings
the population settles somewhere around 180 to 240 and goes up and down on its
own, and most organisms do not become full hunters, they stay in the middle.

There is also a browser version in web/ which runs the same Python with
PyScript, so it needs no server and no install, but the first load takes a few
seconds while it downloads everything. To try it locally, serve the folder and
open it:

    cd web
    python3 -m http.server 8000

web/evolab.py is not written by hand, it is built from the other files, so run
the builder after changing anything:

    .venv/bin/python web/build.py

The builder checks that every module it needs is in its list, because if one is
missing the game runs fine until it hits the code path that uses it and then
dies in the browser with nothing on screen to tell you why. The live version is
on the gh-pages branch, and you update it by pushing the web folder to that
branch with "git subtree push --prefix web origin gh-pages". Not every machine
has git subtree, so if yours doesn't, clone the branch somewhere and copy
index.html and evolab.py into it, then commit and push.

There are a few flags for running it without a monitor, which is how I test it:

    SDL_VIDEODRIVER=dummy .venv/bin/python main.py --frames 420 --seed 5 --shot frame.png

--frames N quits after N frames, --seed N makes the world start the same way
every time, and --shot saves the last frame as an image so you can look at it
afterwards.

devlog/ has 8 short notes in order from the first version up to the last one.
The last one covers the interface work and the changes I made to the ecology
after running the simulation without a window and finding out that most of the
population was only alive because of the random immigrants coming in.

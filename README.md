# EvoLab

An artificial life sim in Python. Around 150 creatures live on a 2D world:
they look for food, run from each other, hunt, and breed. Each one has 8
traits and passes them on with small random changes, so the population
drifts while you sit and watch.

    python3 -m venv .venv
    .venv/bin/python -m ensurepip --upgrade
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python main.py

Space pauses. R replays the last minute. Clicking a creature shows its genome,
its energy and its family line in the panel on the right. The sliders in the
header change how much food spawns, how aggressive the world selects for, the
speed, and the mutation rate.

Food comes in patches, and everything costs energy: moving, having a big body,
having high metabolism. Hunting costs energy too and you can only sprint while
you still have some left, so a chase usually ends when the one being chased
runs out. Hunters get less out of plants, which is why most of the population
stays on plants. If the population drops below 28 the game slowly adds random
new creatures, but on normal settings that almost never happens.

simulation/ is the world and has no pygame in it at all, so it runs without a
window. rendering/ draws it, ui/ is the panels and sliders, and main.py runs
the clock and the replay.

There is a browser version in web/ made with PyScript. It is built from the
same files, so run the builder after changing anything:

    .venv/bin/python web/build.py
    sh web/deploy.sh          (updates the copy on gh-pages)

For testing without a monitor:

    SDL_VIDEODRIVER=dummy .venv/bin/python main.py --frames 300 --shot out.png

devlog/ has the notes I wrote while making it.

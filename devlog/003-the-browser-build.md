DevLog #3 the browser build

The game now runs in the browser, so instead of "install python, make a
venv, pip install, run it" everyone can just open a link and watch their
own evolution unfold. The desktop version is untouched - same code,
same everything.

how it works
The browser runs python through PyScript: it downloads a WebAssembly
build of python plus pygame into the page and runs the game right there.
No server, no install, just an html file that loads python on demand.
The first load takes a few seconds (python is about 10 megabytes) but
after that it just plays, with the same creatures, sliders and
sparklines as the desktop one.

one file
There was one catch: the browser loader only executes a single python
file, and the game is split into nine modules across the project. So i
wrote a build script (web/build.py) that stitches all the modules
together in dependency order, drops the local imports (every name ends
up in one shared namespace anyway) and appends the browser entry point
at the end. Re-run it whenever the code changes and web/evolab.py is
fresh again. No second copy of the game to keep in sync - the browser
build is generated from the real sources.

the loop
The other catch was the game loop. On the desktop the loop blocks on
the clock to hold 60 fps, but in the browser the page drives the frames,
so the loop has to yield back to the event loop with an await instead.
So main() is now async and it picks its frame-wait at startup: in the
browser it awaits a tick and measures the time that passed, on the
desktop it keeps blocking on the clock exactly like before. One loop,
two runtimes, decided by one check.

deploying
To put it on GitHub Pages you push the web folder to the gh-pages
branch (one command, its in the README) and flip the Pages setting in
the repo - the game goes live at yourname.github.io/evolution-sim.
That is the part i could not test from here, so you are the first real
audience for the deployed version.

NEXT
next im gonna make predators! the aggression trait finally gets used -
hunters that chase the slow, and prey that learn to run. and with the
browser build done, i can share the game with a link while it evolves!

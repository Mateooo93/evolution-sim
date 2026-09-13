# DevLog #3 the browser build

it runs in the browser now. instead of install python, make a venv, pip install,
run it, you can open a link. the desktop version is the same code.

pyscript downloads a webassembly build of python plus pygame into the page and
runs the game there. no server involved. the first load takes a few seconds
because python is around 10 megabytes, then it plays. the page is about 500
bytes of html, everything else is python.

the catch is that the browser loader only runs one python file, and the game is
split across the project. so web/build.py stitches the modules together in
dependency order, drops the local imports since every name ends up in one
namespace anyway, and puts the browser entry point on the end. run it after
changing anything and web/evolab.py is current. it is generated, so the browser
version is never a second copy of the game that drifts.

the other catch was the game loop. on the desktop the loop blocks on the clock
to hold 60fps, but in a browser you cannot block, the page drives the frames.
so main() is async and picks how to wait at startup. in the browser it awaits a
tick and measures how long that took. on the desktop it keeps blocking on the
clock like before.

to put it up i pushed the web folder to the gh-pages branch and turned on pages
in the repo settings. it should be live at mateooo93.github.io/evolution-sim.
i could not test that part from here.

next: predators. the aggression trait finally gets used.

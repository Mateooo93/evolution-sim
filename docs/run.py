# entry point for the web version. the game itself is the same code the
# desktop version runs, pyscript.toml fetched it onto the filesystem

import asyncio
import traceback


def _loading(show):
    # the "loading python" line under the canvas
    try:
        from pyscript import window

        status = window.document.getElementById("status")
        if status:
            status.style.display = "" if show else "none"
    except Exception:
        pass


def _show_error(text):
    # a silent death in a browser is impossible to debug, so put it on the page
    print(text)
    try:
        from pyscript import window

        box = window.document.getElementById("err")
        if box:
            box.style.display = "block"
            box.textContent = text
    except Exception:
        pass


async def _start():
    try:
        from main import main

        await main()
    except BaseException:
        _show_error(traceback.format_exc())


try:
    asyncio.get_running_loop()
    asyncio.create_task(_start())
    _loading(False)
except RuntimeError:
    _loading(False)
    asyncio.run(_start())

# this script is used to run the game on a page, no game logic is here, just the loop to start the game and output errors if there are some


import asyncio
import traceback


def _loading(show):
    try:
        from pyscript import window

        status = window.document.getElementById("status")
        if status:
            status.style.display = "" if show else "none"
    except Exception:
        pass


def _show_error(text):
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

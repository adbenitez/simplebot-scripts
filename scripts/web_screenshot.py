import asyncio
import os
import subprocess
import sys
from tempfile import NamedTemporaryFile

import simplebot
from deltachat import Message
from pyppeteer import launch
from simplebot.bot import DeltaBot, Replies


@simplebot.command
def web2image(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Get an screenshot of the given web page.

    Example:
    /web2image https://fsf.org
    """
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=".png", delete=False
    ) as file:
        path = file.name

    subprocess.call((sys.executable, __file__, payload, path))

    if os.stat(path).st_size > 0:
        replies.add(filename=path, quote=message)
    else:
        os.remove(path)
        replies.add(
            text="❌ Failed to take screenshot, is the link correct?", quote=message
        )


async def take_screenshot(url: str, path: str) -> None:
    browser = await launch()
    page = await browser.newPage()
    await page.goto(url)
    await page.screenshot({"path": path})
    await browser.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(take_screenshot(*sys.argv[1:]))  # noqa

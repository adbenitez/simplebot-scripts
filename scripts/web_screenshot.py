"""If you have issues with sandboxing try:
sudo sysctl -w kernel.unprivileged_userns_clone=1
"""

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
    """Get an screen shot of the given web page.

    Example:
    /web2image https://fsf.org
    """
    if not payload.startswith("http"):
        payload = "http://" + payload
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=".png", delete=False
    ) as file:
        path = file.name

    try:
        error = bool(
            subprocess.call((sys.executable, __file__, payload, path), timeout=60)
        )
    except subprocess.TimeoutExpired as ex:
        bot.logger.exception(ex)
        error = True

    if not error and os.stat(path).st_size > 0:
        replies.add(filename=path, quote=message)
    else:
        os.remove(path)
        replies.add(text="❌ Failed to get page, is the link correct?", quote=message)


async def save_page(url: str, path: str) -> None:
    browser = await launch()
    page = await browser.newPage()
    await page.goto(url)
    await page.screenshot({"path": path, "fullPage": "true"})
    await browser.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(save_page(*sys.argv[1:]))  # noqa

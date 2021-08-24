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
    _save_page(".png", bot, payload, message, replies)


@simplebot.command
def web2pdf(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Get the given web page as PDF.

    Example:
    /web2pdf https://fsf.org
    """
    _save_page(".pdf", bot, payload, message, replies)


def _save_page(
    extension: str, bot: DeltaBot, url: str, message: Message, replies: Replies
) -> None:
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=extension, delete=False
    ) as file:
        path = file.name

    subprocess.call((sys.executable, __file__, url, path))

    if os.stat(path).st_size > 0:
        replies.add(filename=path, quote=message)
    else:
        os.remove(path)
        replies.add(text="❌ Failed to get page, is the link correct?", quote=message)


async def save_page(url: str, path: str) -> None:
    browser = await launch()
    page = await browser.newPage()
    await page.goto(url)
    if path.endswith("pdf"):
        await page.pdf({"path": path})
    else:
        await page.screenshot({"path": path, "fullPage": "true"})
    await browser.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(save_page(*sys.argv[1:]))  # noqa

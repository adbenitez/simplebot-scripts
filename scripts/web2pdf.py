"""
requirements:
pdfkit
"""

from tempfile import NamedTemporaryFile

import pdfkit
import simplebot
from deltachat import Message
from simplebot.bot import DeltaBot, Replies


@simplebot.filter
def web2pdf_filter(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Send me any URL in private to save it as PDF."""
    if not message.chat.is_group() and message.text:
        replies.add(filename=_web2pdf(bot, message.text), quote=message)


@simplebot.command
def web2pdf(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Save as PDF the given URL.

    Example:
    /web2pdf https://delta.chat
    """
    replies.add(filename=_web2pdf(bot, payload), quote=message)


def _web2pdf(bot: DeltaBot, url: str) -> str:
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=".pdf", delete=False
    ) as file:
        pdfkit.from_url(url, file.name)
        return file.name

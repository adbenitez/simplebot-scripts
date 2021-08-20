from urllib.parse import quote_plus

import simplebot
from deltachat import Message
from simplebot.bot import Replies
from simplebot_instantview import prepare_html, session  # noqa


@simplebot.filter(trylast=True)
def search_filter(message: Message, replies: Replies) -> None:
    """Send me any text in private to search in the web."""
    if not replies.has_replies() and not message.chat.is_group() and message.text:
        text, html = _search(message.text)
        replies.add(text=text, html=html)


@simplebot.command
def search(payload: str, replies: Replies) -> None:
    """Search the web.

    Example:
    /search download Delta Chat for GNU/Linux
    """
    text, html = _search(payload)
    replies.add(text=text, html=html)


def _search(query: str) -> tuple:
    with session.get(f"https://duckduckgo.com/html?q={quote_plus(query)}") as resp:
        resp.raise_for_status()
        return prepare_html(resp.text)

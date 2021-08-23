import zipfile
import zlib
from tempfile import NamedTemporaryFile

import requests
import simplebot
from deltachat import Message
from simplebot.bot import DeltaBot, Replies
from simplebot_instantview import prepare_html, prepare_url, session  # noqa

zlib.Z_DEFAULT_COMPRESSION = 9


@simplebot.command
def compress(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Get a web page in a compressed archive.

    Example:
    /compress https://fsf.org
    """
    try:
        with session.get(prepare_url(payload, bot)) as resp:
            resp.raise_for_status()
            _, html = prepare_html(
                bot.self_contact.addr, resp.url, resp.text, "/compress "
            )
        replies.add(filename=save_htmlzip(bot, html), quote=message)
    except requests.exceptions.RequestException as ex:
        bot.logger.exception(ex)
        replies.add(text="❌ Invalid request", quote=message)


def save_htmlzip(bot, html) -> str:
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=".html.zip", delete=False
    ) as file:
        path = file.name
    with open(path, "wb") as f:
        with zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as fzip:
            fzip.writestr("index.html", html)
    return path

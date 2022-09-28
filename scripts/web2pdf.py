"""
requirements:
pdfkit

you also need to install wkhtmltopdf package, Debian/Ubuntu example:

$ sudo apt-get install wkhtmltopdf

Warning! Version in debian/ubuntu repos have reduced functionality (because it compiled without the wkhtmltopdf QT patches), such as adding outlines, headers, footers, TOC etc. To use this options you should install static binary from wkhtmltopdf site: https://wkhtmltopdf.org/
"""
import re
from tempfile import NamedTemporaryFile

import pdfkit
import simplebot
from deltachat import Message
from simplebot.bot import DeltaBot, Replies


@simplebot.filter
def web2pdf_filter(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Send me any URL to save it as PDF."""
    match = re.search(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|"
        r"(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        message.text,
    )
    if match:
        url = match.group()
    elif message.text and not message.chat.is_multiuser():
        url = message.text
    else:
        return
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=".pdf", delete=False
    ) as file:
        try:
            pdfkit.from_url(url, file.name)
            replies.add(filename=file.name, quote=message)
        except Exception:
            replies.add(
                text="Failed to retrieve web site, is the URL correct?", quote=message
            )

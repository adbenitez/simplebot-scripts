"""
To use first install dependencies:
    pip install "qrcode[pil]"
"""

import io
from urllib.parse import unquote_plus

import qrcode
import simplebot
from deltachat import Message
from simplebot.bot import DeltaBot, Replies


@simplebot.filter
def verification_filter(message: Message) -> None:
    """Send me your OPENPGP4FPR link and I will verify you."""
    link = message.text.split(maxsplit=1)[0]
    if link.lower().startswith("openpgp4fpr:") and "g=" not in link:
        if f"a={message.get_sender_contact().addr}" in unquote_plus(link):
            message.account.qr_setup_contact(link)


@simplebot.command
def verify(bot: DeltaBot, replies: Replies) -> None:
    """Get the bot's verification QR code."""
    buffer = io.BytesIO()
    qrcode.make(bot.account.get_setup_contact_qr()).save(buffer, format="jpeg")
    buffer.seek(0)
    replies.add(filename="qr.jpg", bytefile=buffer)

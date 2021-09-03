"""
To use first install dependencies:
    pip install "qrcode[pil]"
    pip install pyzbar

You will need to install the zbar shared library to extract QR data from images:
    sudo apt-get install libzbar0
"""

import io
from urllib.parse import unquote_plus

import qrcode
import simplebot
from deltachat import Message
from PIL import Image
from pyzbar import pyzbar
from simplebot.bot import DeltaBot, Replies


@simplebot.filter
def verification_filter(message: Message) -> None:
    """Send me your contact QR or OPENPGP4FPR link in private and I will verify you."""
    if message.chat.is_group():
        return
    if message.is_image():
        results = pyzbar.decode(Image.open(message.filename))
        link = results[0].data.decode() if results else ""
    else:
        link = message.text
    link = link.split(maxsplit=1)[0]
    addr = message.get_sender_contact().addr
    if link.lower().startswith("openpgp4fpr:") and f"a={addr}" in unquote_plus(link):
        message.account.qr_setup_contact(link)


@simplebot.command
def contactQR(bot: DeltaBot, replies: Replies) -> None:
    """Get the bot's verification QR code."""
    buffer = io.BytesIO()
    qrcode.make(bot.account.get_setup_contact_qr()).save(buffer, format="jpeg")
    buffer.seek(0)
    replies.add(filename="qr.jpg", bytefile=buffer)

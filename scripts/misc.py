"""Miscellaneous small commands and filters."""

import io
from urllib.parse import unquote_plus

import simplebot


@simplebot.hookimpl
def deltabot_member_added(bot, chat, contact, actor) -> None:
    if (
        chat.get_name() == "Bot Tower"
        and not bot.is_admin(actor.addr)
        and not bot.is_admin(contact.addr)
    ):
        chat.remove_contact(contact)


@simplebot.filter
def filter_messages(message, bot) -> None:
    """Send me OPENPGP4FPR links to verify yourself."""
    if message.text.startswith("OPENPGP4FPR:") and "g=" not in message.text:
        addr = message.get_sender_contact().addr
        if "a=" + addr in unquote_plus(message.text) or bot.is_admin(addr):
            bot.account.qr_setup_contact(message.text)


try:
    import requests

    @simplebot.command
    def chiste(payload, replies) -> None:
        """Envía un chiste al azar."""
        import bs4
        with requests.get("http://www.chistes.com/ChisteAlAzar.asp?n=1") as resp:
            soup = bs4.BeautifulSoup(resp.text, "html.parser")
            joke = soup.find("div", class_="chiste").get_text()
            replies.add(text=joke)

    @simplebot.command
    def insult(payload, message, replies) -> None:
        """insult quoted message."""
        with requests.get(
            f"https://evilinsult.com/generate_insult.php?lang={payload}&type=json"
        ) as resp:
            replies.add(text=resp.json()["insult"], quote=message.quote)

    @simplebot.command
    def advice(replies) -> None:
        """get random advice."""
        with requests.get("https://api.adviceslip.com/advice") as resp:
            replies.add(text=resp.json()["slip"]["advice"])

    @simplebot.command
    def chuckjoke(replies) -> None:
        """get random Chuck Norris joke."""
        with requests.get(
            "http://api.icndb.com/jokes/random?escape=javascript"
        ) as resp:
            replies.add(text=resp.json()["value"]["joke"])

    @simplebot.command
    def joke(payload, replies) -> None:
        """get random joke."""
        with requests.get(
            f"https://v2.jokeapi.dev/joke/Any?format=txt&contains={payload}"
        ) as resp:
            replies.add(text=resp.text)

    @simplebot.command
    def dadjoke(replies) -> None:
        """get random dad joke."""
        headers = {
            "User-Agent": "SimpleBot (https://github.com/simplebot-org/simplebot)",
            "Accept": "text/plain",
        }
        with requests.get("https://icanhazdadjoke.com/", headers=headers) as resp:
            replies.add(text=resp.text)


except ImportError as ex:
    print("WARNING:", ex)


try:
    import upsidedown

    @simplebot.command
    def flip(payload, replies) -> None:
        """Flip given text."""
        replies.add(text=upsidedown.transform(payload or "no text given"))


except ImportError as ex:
    print("WARNING:", ex)


try:
    import imgkit

    @simplebot.command(admin=True)
    def html2img(payload, message, replies) -> None:
        """html to image"""
        options = {
            "format": "webp",
            "width": "370",
            "quality": "80",
        }
        img = imgkit.from_url(payload, False, options=options)
        replies.add(filename="html.webp", bytefile=io.BytesIO(img), quote=message)


except ImportError as ex:
    print("WARNING:", ex)


@simplebot.command(name="/echoAs")
def echoas(payload, replies) -> None:
    """Echo back text but impersonating the given name, expected arguments: one line with the name and another line with the text."""
    name, text = payload.split("\n", maxsplit=1)
    replies.add(text=text, sender=name)


@simplebot.command
def text2html(payload, replies) -> None:
    """Reply back received text but as html message."""
    index = payload.find("<html>")
    if index > 0:
        replies.add(text=payload[:index], html=payload[index:])
    else:
        replies.add(html=payload)


@simplebot.command
def file2html(payload, message, replies) -> None:
    """Reply back received HTML file as html message."""
    with open(message.filename) as file:
        replies.add(text=payload, html=file.read())

"""Miscellaneous small commands and filters."""

import functools
import io
import random
import re
from datetime import datetime, timedelta
from urllib.parse import quote

import bs4
import requests
import simplebot

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0"
    }
)
session.request = functools.partial(session.request, timeout=30)  # type: ignore


@simplebot.hookimpl
def deltabot_member_added(bot, chat, contact, actor) -> None:
    if (
        chat.get_name() == "Bot Tower"
        and not bot.is_admin(actor.addr)
        and not bot.is_admin(contact.addr)
    ):
        chat.remove_contact(contact)


@simplebot.filter
def html2file_filter(message, replies) -> None:
    """Send me an html message in private to get html content as file."""
    if not message.chat.is_multiuser() and message.has_html():
        replies.add(
            filename="message.html",
            bytefile=io.BytesIO(message.html.encode(errors="replace")),
            quote=message,
        )


@simplebot.command
def bolita(replies) -> None:
    """Los resultados de la bolita (lotería de la Florida)"""
    import feedparser

    with session.get("https://flalottery.com/video/en/theWinningNumber.xml") as resp:
        resp.raise_for_status()
        d = feedparser.parse(resp.text)
    pick3, pick4 = "", ""
    regex = re.compile(r"([\d-]+) for (\w+) ([\d/]+)")
    for entry in d.entries:
        title = entry.title.lower()
        if title.startswith(("pick 3", "pick 4")):
            text = ""
            for result in regex.findall(entry.description):
                text += f"{result[2]} {'☀️ Día' if result[1] == 'Midday' else '🌙 Noche'}: {result[0]}\n"
            if title.startswith("pick 3"):
                pick3 = text
            else:
                pick4 = text
    assert pick3 and pick4
    replies.add(text=f"**🎰 Resultados**\n\n**PICK 3**\n{pick3}\n**PICK 4**\n{pick4}")


@simplebot.command
def adivinanza(bot, replies) -> None:
    """Probabilidad y adivinanza para la bolita (lotería de la Florida)"""
    with session.get("https://bolitacuba.com/probabilidad-y-adivinanza/") as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    url = soup.find(class_="alm-reveal").a["href"]
    base_url, resource = url.rstrip("/").rsplit("/", maxsplit=1)
    resource = (
        datetime.strptime(resource.split("pya-")[-1], "%m-%d-%Y") + timedelta(days=1)
    ).strftime("pya-%m-%d-%Y")
    try:
        with session.get(f"{base_url}/{resource}/") as resp:
            resp.raise_for_status()
            soup = bs4.BeautifulSoup(resp.text, "html5lib")
    except requests.HTTPError as err:
        bot.logger.exception(err)
        with session.get(url) as resp:
            resp.raise_for_status()
            soup = bs4.BeautifulSoup(resp.text, "html5lib")
    soup = soup.find(class_="entry-content")
    for tag in soup(class_="code-block"):
        tag.extract()
    for tag in soup("i", class_="fa-sun"):
        tag.replace_with("☀️")
    for tag in soup("i", class_="fa-moon"):
        tag.replace_with("🌙")
    replies.add(text=_soup2text(soup))


@simplebot.command
def chiste(replies) -> None:
    """Envía un chiste al azar."""
    while True:
        text = random.choice(
            (_chistes, _chistalia, _todo_chistes, _elclubdeloschistes)
        )()
        if text:
            break
    replies.add(text=text)


def _chistes() -> str:
    with session.get("http://www.chistes.com/ChisteAlAzar.asp?n=2") as resp:
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    return _soup2text(soup.find(class_="chiste")) + "\n\nFuente: http://www.chistes.com"


def _chistalia() -> str:
    with session.get("https://chistalia.es/aleatorio/") as resp:
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    return _soup2text(soup.blockquote) + "\n\nFuente: https://chistalia.es"


def _todo_chistes() -> str:
    with session.get("http://todo-chistes.com/chistes-al-azar") as resp:
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    return (
        _soup2text(soup.find(class_="field-chiste"))
        + "\n\nFuente: http://todo-chistes.com"
    )


def _elclubdeloschistes() -> str:
    with session.get("https://elclubdeloschistes.com/azar.php") as resp:
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    soup.b.extract()
    for tag in soup("a"):
        tag.extract()
    text = _soup2text(soup.find(class_="texto"))
    text = text[: text.rfind("ID:")].strip()
    if not text:
        return ""
    return text + "\n\nFuente: https://elclubdeloschistes.com"


def _soup2text(soup: bs4.BeautifulSoup) -> str:
    for tag in soup("br"):
        tag.replace_with("\n")
    lines = []
    for line in soup.get_text().split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


@simplebot.command
def insult(payload, message, replies) -> None:
    """insult quoted message."""
    with session.get(
        f"https://evilinsult.com/generate_insult.php?lang={payload}&type=json"
    ) as resp:
        replies.add(text=resp.json()["insult"], quote=message.quote)


@simplebot.command
def advice(replies) -> None:
    """get random advice."""
    with session.get("https://api.adviceslip.com/advice") as resp:
        replies.add(text=resp.json()["slip"]["advice"])


@simplebot.command
def chuckjoke(replies) -> None:
    """get random Chuck Norris joke."""
    with session.get("http://api.icndb.com/jokes/random?escape=javascript") as resp:
        replies.add(text=resp.json()["value"]["joke"])


@simplebot.command
def joke(payload, replies) -> None:
    """get random joke."""
    with session.get(
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
    with session.get("https://icanhazdadjoke.com/", headers=headers) as resp:
        replies.add(text=resp.text)


@simplebot.command
def flip(payload, replies) -> None:
    """Flip given text."""
    import upsidedown

    replies.add(text=upsidedown.transform(payload or "no text given"))


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
    with open(message.filename, encoding="utf-8") as file:
        replies.add(text=payload, html=file.read())


@simplebot.command
def wttr(payload, message, replies) -> None:
    """Search weather info from wttr.in"""
    with session.get(f"https://wttr.in/{quote(payload)}?Fnp&lang=en") as resp:
        replies.add(text="Result from wttr.in", html=resp.text, quote=message)

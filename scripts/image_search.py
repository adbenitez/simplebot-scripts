import functools
import io
import mimetypes
import random
import re
from typing import Generator
from urllib.parse import quote, quote_plus

import bs4
import requests
import simplebot
from deltachat import Message
from simplebot.bot import DeltaBot, Replies

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0"
    }
)
session.request = functools.partial(session.request, timeout=15)  # type: ignore


@simplebot.command
def image(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Get an image based on the given text.

    Example:
    /image cats and dogs
    """
    _image_cmd(1, bot, payload, message, replies)


@simplebot.command
def image5(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Search for images, returns up to five results.

    Example:
    /image5 roses
    """
    _image_cmd(5, bot, payload, message, replies)


def _image_cmd(
    img_count: int, bot: DeltaBot, payload: str, message: Message, replies: Replies
) -> None:
    if not payload:
        replies.add(text="❌ No text given", quote=message)
        return
    imgs = img_count
    for filename, data in _get_images(bot, payload):
        replies.add(filename=filename, bytefile=io.BytesIO(data))
        imgs -= 1
        if imgs <= 0:
            break
    if imgs == img_count:
        replies.add(text="❌ No results", quote=message)


def _get_images(bot: DeltaBot, query: str) -> Generator:
    img_providers = [_google_imgs, _startpage_imgs, _dogpile_imgs]
    img_providers_low = [_alphacoders, _unsplash, _everypixel]
    while img_providers:
        provider = random.choice(img_providers)
        img_providers.remove(provider)
        try:
            bot.logger.debug("Trying %s", provider)
            for img_url in provider(query):
                with session.get(img_url) as resp:
                    resp.raise_for_status()
                    filename = "image" + (get_extension(resp) or ".jpg")
                    yield filename, resp.content
        except Exception as err:
            bot.logger.exception(err)
        if not img_providers and img_providers_low:
            img_providers.extend(img_providers_low)
            img_providers_low.clear()


def _google_imgs(query: str) -> set:
    url = f"https://www.google.com/search?tbm=isch&sout=1&q={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    links = set()
    for table in soup("table"):
        for img in table("img"):
            if img["src"].startswith("data:"):
                continue
            links.add(img["src"])
    return links


def _startpage_imgs(query: str) -> set:
    url = f"https://startpage.com/do/search?cat=pics&cmd=process_search&query={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        url = resp.url
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    index = url.find("/", 8)
    if index == -1:
        root = url
    else:
        root = url[:index]
        url = url.rsplit("/", 1)[0]
    links = set()
    for div in soup(class_="image-container"):
        if not div.img or div.img.startswith("data:"):
            continue
        img = re.sub(r"^(//.*)", rf"{root.split(':', 1)[0]}:\1", div.img)
        img = re.sub(r"^(/.*)", rf"{root}\1", img)
        if not re.match(r"^https?://", img):
            img = f"{url}/{img}"
        links.add(img)
    return links


def _alphacoders(query: str) -> set:
    url = f"https://pics.alphacoders.com/search?t={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    links = set()
    for tag in soup("img", class_="img-thumb"):
        if tag["src"].startswith("data:"):
            continue
        links.add(tag["src"])
    return links


def _unsplash(query: str) -> set:
    url = f"https://unsplash.com/s/photos/{quote(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    links = set()
    for tag in soup("img", itemprop="thumbnailUrl"):
        if tag["src"].startswith("data:"):
            continue
        links.add(tag["src"])
    return links


def _everypixel(query: str) -> set:
    url = f"https://www.everypixel.com/search?meaning=&stocks_type=free&media_type=0&page=1&q={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    links = set()
    for tag in soup(class_="thumb"):
        if tag.img["src"].startswith("data:"):
            continue
        links.add(tag.img["src"])
    return links


def _dogpile_imgs(query: str) -> set:
    url = f"https://www.dogpile.com/search/images?q={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    soup = soup.find("div", class_="mainline-results")
    if not soup:
        return set()
    links = set()
    for anchor in soup("a"):
        if anchor.img:
            links.add(anchor["href"])
    return links


def get_extension(resp: requests.Response) -> str:
    disp = resp.headers.get("content-disposition")
    if disp is not None and re.findall("filename=(.+)", disp):
        fname = re.findall("filename=(.+)", disp)[0].strip('"')
    else:
        fname = resp.url.split("/")[-1].split("?")[0].split("#")[0]
    if "." in fname:
        ext = "." + fname.rsplit(".", maxsplit=1)[-1]
    else:
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        ext = mimetypes.guess_extension(ctype) or ""
    return ext

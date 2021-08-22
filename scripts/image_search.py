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
        "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }
)
session.request = functools.partial(session.request, timeout=30)  # type: ignore


@simplebot.command
def image(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Get an image based on the given text."""
    _image_cmd(1, bot, payload, message, replies)


@simplebot.command
def image5(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Search for images, returns 5 results."""
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
    img_providers = [_wallpaperflare, _unsplash, _everypixel, _dogpile_imgs]
    img_providers_low = [_alphacoders, _google_imgs, _startpage_imgs]
    while img_providers:
        provider = random.choice(img_providers)
        img_providers.remove(provider)
        try:
            bot.logger.debug("Trying %s", provider)
            imgs = provider(query)
            if imgs:
                for img_url in imgs:
                    with session.get(img_url) as resp:
                        resp.raise_for_status()
                        filename = "image" + (get_extension(resp) or ".jpg")
                        yield filename, resp.content
        except Exception as err:
            bot.logger.exception(err)
            if not img_providers and img_providers_low:
                img_providers.extend(img_providers_low)
                img_providers_low.clear()


def _google_imgs(query: str) -> list:
    url = f"https://www.google.com/search?tbm=isch&sout=1&q={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    imgs = []
    for table in soup("table"):
        for img in table("img"):
            if img["src"].startswith("data:"):
                continue
            imgs.append(img["src"])
    return imgs


def _startpage_imgs(query: str) -> list:
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
    imgs = []
    for div in soup(class_="image-container"):
        if div.img.startswith("data:"):
            continue
        img = re.sub(r"^(//.*)", r"{}:\1".format(root.split(":", 1)[0]), div.img)
        img = re.sub(r"^(/.*)", r"{}\1".format(root), img)
        if not re.match(r"^https?://", img):
            img = f"{url}/{img}"
        imgs.append(img)
    return imgs


def _alphacoders(query: str) -> list:
    url = f"https://pics.alphacoders.com/search?t={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    imgs = []
    for tag in soup("img", class_="img-thumb"):
        if tag.img["src"].startswith("data:"):
            continue
        imgs.append(tag.img["src"])
    return imgs


def _wallpaperflare(query: str) -> list:
    url = f"https://www.wallpaperflare.com/search?width=&height=&wallpaper={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    soup = soup.find(id="gallery")
    imgs = []
    for tag in soup("img", attrs={"data-src": True}):
        if tag["data-src"].startswith("data:"):
            continue
        imgs.append(tag["data-src"])
    return imgs


def _unsplash(query: str) -> list:
    url = f"https://unsplash.com/s/photos/{quote(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    imgs = []
    for tag in soup("img", itemprop="thumbnailUrl"):
        if tag["src"].startswith("data:"):
            continue
        imgs.append(tag["src"])
    return imgs


def _everypixel(query: str) -> list:
    url = f"https://www.everypixel.com/search?meaning=&stocks_type=free&media_type=0&page=1&q={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    imgs = []
    for tag in soup(class_="thumb"):
        if tag.img["src"].startswith("data:"):
            continue
        imgs.append(tag.img["src"])
    return imgs


def _dogpile_imgs(query: str) -> list:
    url = f"https://www.dogpile.com/search/images?q={quote_plus(query)}"
    with session.get(url) as resp:
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html5lib")
    soup = soup.find("div", class_="mainline-results")
    if not soup:
        return []
    links = []
    for anchor in soup("a"):
        if anchor.img:
            links.append(anchor["href"])
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

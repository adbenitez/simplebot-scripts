import os

import simplebot
import youtube_dl
from deltachat import Message
from simplebot.bot import DeltaBot, Replies
from simplebot_dowloader import queue_download


@simplebot.command
def yt2video(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Download video from YouTube.

    Example:
    /yt2video https://www.youtube.com/watch?v=tZpxR8iM19s
    """
    queue_download(message.text, bot, message, replies, download_ytvideo)


@simplebot.command
def yt2audio(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Download audio from YouTube video.

    Example:
    /yt2audio https://www.youtube.com/watch?v=tZpxR8iM19s
    """
    queue_download(message.text, bot, message, replies, download_ytaudio)


def download_ytvideo(url: str, folder: str, max_size: int) -> str:
    opts = {
        "format": f"best[filesize<{max_size}]",
        "max_downloads": 1,
        "socket_timeout": 15,
        "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
    }
    with youtube_dl.YoutubeDL(opts) as yt:
        yt.download([url])
    return os.path.join(folder, os.listdir(folder)[0])


def download_ytaudio(url: str, folder: str, max_size: int) -> str:
    opts = {
        "format": f"bestaudio[filesize<{max_size}]",
        "max_downloads": 1,
        "socket_timeout": 15,
        "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
    }
    with youtube_dl.YoutubeDL(opts) as yt:
        yt.download([url])
    return os.path.join(folder, os.listdir(folder)[0])

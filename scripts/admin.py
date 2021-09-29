"""Administrator tools."""

import os
import subprocess
from typing import List, Optional, Set

import deltachat
import psutil
import simplebot
from deltachat import account_hookimpl
from simplebot.bot import DeltaBot, Replies


class AccountPlugin:
    def __init__(self, bot: DeltaBot) -> None:
        self.bot = bot

    def _clean_group(self, chat_id: int, msg_id: int) -> None:
        chat = self.bot.get_chat(chat_id)
        if not chat.is_group():
            return
        error = self.bot.account.get_message_by_id(msg_id).error
        for c in chat.get_contacts():
            if f"<{c.addr}>" in error:
                # TODO: remove after N errors
                chat.remove_contact(c)

    @account_hookimpl
    def ac_process_ffi_event(self, ffi_event):
        if ffi_event.name == "DC_EVENT_MSG_FAILED":
            try:
                self._clean_group(ffi_event.data1, ffi_event.data2)
            except Exception as ex:
                self.bot.logger.exception(ex)


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    bot.account.add_account_plugin(AccountPlugin(bot))


@simplebot.hookimpl(tryfirst=True)
def deltabot_incoming_message(bot: DeltaBot, message) -> Optional[bool]:
    contact = message.get_sender_contact()
    if contact.addr in get_banned(bot):
        contact.block()
        bot.plugins._pm.hook.deltabot_ban(bot=bot, contact=contact)
        contact.block()
        return True
    return None


@simplebot.hookimpl
def deltabot_member_added(bot: DeltaBot, chat, contact) -> None:
    if contact.addr in get_banned(bot):
        chat.remove_contact(contact)
        contact.block()
        bot.plugins._pm.hook.deltabot_ban(bot=bot, contact=contact)
        contact.block()


@simplebot.command(admin=True)
def stats(replies: Replies) -> None:
    """Get bot and computer state."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(os.path.expanduser("~/.simplebot/"))
    proc = psutil.Process()
    botmem = proc.memory_full_info()
    replies.add(
        text="**🖥️ Computer Stats:**\n"
        f"CPU: {psutil.cpu_percent(interval=0.1)}%\n"
        f"Memory: {sizeof_fmt(mem.used)}/{sizeof_fmt(mem.total)}\n"
        f"Swap: {sizeof_fmt(swap.used)}/{sizeof_fmt(swap.total)}\n"
        f"Disk: {sizeof_fmt(disk.used)}/{sizeof_fmt(disk.total)}\n\n"
        "**🤖 Bot Stats:**\n"
        f"CPU: {proc.cpu_percent(interval=0.1)}%\n"
        f"Memory: {sizeof_fmt(botmem.rss)}\n"
        f"Swap: {sizeof_fmt(botmem.swap if 'swap' in botmem._fields else 0)}\n"
        f"SimpleBot: {simplebot.__version__}\n"
        f"DeltaChat: {deltachat.__version__}\n"
    )


@simplebot.command(admin=True)
def ban2(bot: DeltaBot, payload: str, replies: Replies) -> None:
    """ban forever."""
    banned = add_banned(bot, payload.split()) if payload else get_banned(bot)
    replies.add(text=f"Banned ({len(banned)})", html="<br>".join(banned))


@simplebot.command(admin=True)
def move(bot: DeltaBot, payload: str, message) -> None:
    """move to group."""
    c = message.quote.get_sender_contact()
    message.chat.remove_contact(c)
    chat = bot.get_chat(int(payload.strip("f")))
    chat.add_contact(c)
    if "f" in payload:
        bot.account.forward_messages([message.quote], chat)


@simplebot.command(admin=True)
def unban2(bot: DeltaBot, payload: str, replies: Replies) -> None:
    """unban forever."""
    if payload:
        banned = del_banned(bot, payload.split())
        replies.add(text=f"Banned ({len(banned)})", html="<br>".join(banned))


@simplebot.command(admin=True)
def kick(message) -> None:
    """Kick from group the sender of the quoted message."""
    message.chat.remove_contact(message.quote.get_sender_contact())


@simplebot.command(admin=True)
def add(message) -> None:
    """Add quoted unknown sender to group."""
    message.chat.add_contact(message.quote.get_sender_contact())


@simplebot.command(admin=True)
def destroy(bot: DeltaBot, message) -> None:
    """Destroy group."""
    for c in message.chat.get_contacts():
        if c != bot.self_contact:
            message.chat.remove_contact(c)


@simplebot.command(admin=True)
def config(payload: str, bot: DeltaBot, replies: Replies) -> None:
    """set config"""
    args = payload.split(maxsplit=1)
    if len(args) == 2:
        key, val = args
        bot.account.set_config(key, val)
    else:
        replies.add(text=f"{key}: {bot.account.get_config(key)}")


@simplebot.command(name="/exec", admin=True)
def exec_cmd(payload: str, replies: Replies) -> None:
    """Execute shell command."""
    replies.add(text=subprocess.check_output(payload, shell=True))


@simplebot.command(name="/eval", admin=True)
def cmd_eval(payload, bot, command, message, replies) -> None:  # noqa
    """Evaluate python code."""
    eval(payload)


def get_banned(bot: DeltaBot) -> Set[str]:
    return set((bot.get("banned", scope=__name__) or "").split())


def del_banned(bot: DeltaBot, addrs: List[str]) -> Set[str]:
    banned = get_banned(bot) - set(addrs)
    bot.set("banned", " ".join(banned), scope=__name__)
    for addr in addrs:
        contact = bot.get_contact(addr)
        contact.unblock()
        bot.plugins._pm.hook.deltabot_unban(bot=bot, contact=contact)
    return banned


def add_banned(bot: DeltaBot, addrs: List[str]) -> Set[str]:
    banned = get_banned(bot).union(set(addrs))
    bot.set("banned", " ".join(banned), scope=__name__)
    for addr in addrs:
        contact = bot.get_contact(addr)
        contact.block()
        bot.plugins._pm.hook.deltabot_ban(bot=bot, contact=contact)
        contact.block()
    return banned


def sizeof_fmt(num: float) -> str:
    suffix = "B"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)  # noqa
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)  # noqa

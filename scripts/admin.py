"""Administrator tools."""

import subprocess
from typing import Optional

import simplebot
from deltachat import account_hookimpl


class AccountPlugin:
    def __init__(self, bot):
        self.bot = bot

    def _clean_group(self, chat_id: int, msg_id: int) -> None:
        chat = self.bot.get_chat(chat_id)
        if not chat.is_group():
            return
        error = self.bot.account.get_message_by_id(msg_id).error
        for c in chat.get_contacts():
            if "<{}>".format(c.addr) in error:
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
def deltabot_init(bot) -> None:
    bot.account.add_account_plugin(AccountPlugin(bot))


@simplebot.hookimpl(tryfirst=True)
def deltabot_incoming_message(bot, message) -> Optional[bool]:
    contact = message.get_sender_contact()
    if contact.addr in get_banned(bot):
        contact.block()
        bot.plugins._pm.hook.deltabot_ban(bot=bot, contact=contact)
        contact.block()
        return True
    return None


@simplebot.hookimpl
def deltabot_member_added(bot, chat, contact) -> None:
    if contact.addr in get_banned(bot):
        chat.remove_contact(contact)
        contact.block()
        bot.plugins._pm.hook.deltabot_ban(bot=bot, contact=contact)
        contact.block()


@simplebot.command(admin=True)
def ban2(bot, payload, replies) -> None:
    """ban forever."""
    if payload:
        banned = add_banned(bot, payload.split())
    else:
        banned = get_banned(bot)
    replies.add(text="Banned ({}):\n\n{}".format(len(banned), "\n".join(banned)))


@simplebot.command(admin=True)
def move(bot, payload, message) -> None:
    """move to group."""
    c = message.quote.get_sender_contact()
    message.chat.remove_contact(c)
    chat = bot.get_chat(int(payload.strip("f")))
    chat.add_contact(c)
    if "f" in payload:
        bot.account.forward_messages([message.quote], chat)


@simplebot.command(admin=True)
def unban2(bot, payload, replies) -> None:
    """unban forever."""
    if payload:
        banned = del_banned(bot, payload.split())
        replies.add(text="Banned ({}):\n\n{}".format(len(banned), "\n".join(banned)))


@simplebot.command(admin=True)
def kick(message) -> None:
    """Kick from group the sender of the quoted message."""
    message.chat.remove_contact(message.quote.get_sender_contact())


@simplebot.command(admin=True)
def add(message) -> None:
    """Add quoted unknown sender to group."""
    message.chat.add_contact(message.quote.get_sender_contact())


@simplebot.command(admin=True)
def destroy(message, bot) -> None:
    """Destroy group."""
    for c in message.chat.get_contacts():
        if c != bot.self_contact:
            message.chat.remove_contact(c)


@simplebot.command(admin=True)
def config(payload, bot, replies) -> None:
    """set config"""
    args = payload.split(maxsplit=1)
    if len(args) == 2:
        key, val = args
        bot.account.set_config(key, val)
    else:
        replies.add(text="{}: {}".format(key, bot.account.get_config(key)))


@simplebot.command(name="/exec", admin=True)
def exec_cmd(payload, replies) -> None:
    """Execute shell command."""
    replies.add(text=subprocess.check_output(payload, shell=True))


@simplebot.command(name="/eval", admin=True)
def cmd_eval(payload, bot, command, message, replies) -> None:  # noqa
    """Evaluate python code."""
    eval(payload)


def get_banned(bot) -> list:
    return (bot.get("banned", scope=__name__) or "").split()


def del_banned(bot, addrs) -> list:
    banned = [addr for addr in get_banned(bot) if addr not in addrs]
    bot.set("banned", " ".join(banned), scope=__name__)
    for addr in addrs:
        contact = bot.get_contact(addr)
        contact.unblock()
        bot.plugins._pm.hook.deltabot_unban(bot=bot, contact=contact)
        contact.unblock()

    return banned


def add_banned(bot, addrs) -> list:
    banned = get_banned(bot) + addrs
    bot.set("banned", " ".join(banned), scope=__name__)
    for addr in addrs:
        contact = bot.get_contact(addr)
        contact.block()
        bot.plugins._pm.hook.deltabot_ban(bot=bot, contact=contact)
        contact.block()

    return banned

# requirements:
# toml==0.10.2

import json
import os
import shutil
import string
from zipfile import ZipFile

import simplebot
import toml
from deltachat import Message
from deltachat.capi import lib
from deltachat.cutil import as_dc_charpointer, from_dc_charpointer
from simplebot.bot import DeltaBot, Replies

FOLDER = ""
META_FIELDS = [
    "name",
    "description",
    "id",
    "version_name",
    "version_code",
    "author",
    "author_email",
]


@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    global FOLDER
    FOLDER = os.path.join(os.path.dirname(bot.account.db_path), __name__)
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)


@simplebot.filter(admin=True)
def filter_messages(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Webxdc store"""
    if message.chat.is_group() or not is_webxdc(message.filename):
        return

    addr = message.get_sender_contact().addr
    meta = get_metadata(message.filename)
    if not check_fields(meta):
        fields = "\n".join(META_FIELDS)
        replies.add(
            text=f"❌ Your webxdc's manifest.toml must include an [store] section with all this fields:\n\n{fields}",
            quote=message,
        )
        return

    valid_chars = string.ascii_letters + string.digits + "."
    for c in meta["id"]:
        if c not in valid_chars:
            replies.add(
                text=f"❌ Invalid ID, only letters and numbers allowed", quote=message
            )
            return

    if meta["author_email"] == addr or bot.is_admin(addr):
        path = os.path.join(FOLDER, meta["id"] + ".xdc")
        if os.path.exists(path):
            meta2 = get_metadata(path)
            if meta["author_email"] == meta2["author_email"]:
                if meta["version_code"] <= meta2["version_code"]:
                    replies.add(
                        text=f"❌ version_code must be superior to previous release: {meta2['version_code']}",
                        quote=message,
                    )
                    return
            else:
                replies.add(
                    text=f"❌ A webxdc with ID == {meta['id']!r} was already published by another author",
                    quote=message,
                )
                return

        shutil.copy(message.filename, path)
        replies.add(text="✔️Published", quote=message)
    else:
        replies.add(
            text="❌ Manifest field author_email must match your email address",
            quote=message,
        )


@simplebot.command(name="/list")
def list_cmd(replies: Replies) -> None:
    """Get list of available webxdc"""
    text = ["**Webxdc List:**"]
    for name in os.listdir(FOLDER):
        path = os.path.join(FOLDER, name)
        if is_webxdc(path):
            name = os.path.splitext(name)[0]
            text.append(f"/download_{name}")

    replies.add(text="\n\n".join(text))


@simplebot.command
def download(payload: str, message: Message, replies: Replies) -> None:
    """Download the webxdc with the given ID"""
    path = os.path.join(FOLDER, payload + ".xdc")
    if os.path.exists(path):
        replies.add(filename=path)
    else:
        replies.add(text=f"❌ Unknow webxdc ID", quote=message)


@simplebot.command(admin=True)
def delete(payload: str, message: Message, replies: Replies) -> None:
    """Delete the webxdc with the given ID"""
    path = os.path.join(FOLDER, payload + ".xdc")
    if os.path.exists(path):
        os.remove(path)
        replies.add(filename="✔️Deleted")
    else:
        replies.add(text=f"❌ Unknow webxdc ID", quote=message)


@simplebot.command(admin=True)
def update(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Send the latest version of the quoted webxdc along with its current state"""
    quote = message.quote
    if (
        not quote
        or not is_webxdc(quote.filename)
        or quote.get_sender_contact() != bot.self_contact
    ):
        replies.add(text=f"❌ Wrong usage", quote=message)
        return

    meta = get_metadata(quote.filename)
    path = os.path.join(FOLDER, meta["id"] + ".xdc")
    if os.path.exists(path):
        msg = replies._create_message(filename=path)
        quote.chat.set_draft(msg)

        updates = json.loads(
            from_dc_charpointer(
                lib.dc_get_webxdc_status_updates(
                    bot.account._dc_context,
                    quote.id,
                    0,
                )
            )
        )
        if updates and updates[0].get("payload", {}).get("score") is not None:
            scores = {}
            for update in updates:
                payload = update["payload"]
                addr = payload["addr"]
                old_payload = scores.setdefault(addr, update)["payload"]
                if old_payload["score"] < payload["score"]:
                    scores[addr] = update
            updates = list(scores.values())
        for update in updates:
            lib.dc_send_webxdc_status_update(
                bot.account._dc_context,
                msg.id,
                as_dc_charpointer(json.dumps(update)),
                as_dc_charpointer("sync"),
            )

        quote.chat.send_msg(msg)
    else:
        replies.add(text=f"❌ Unknow webxdc ID", quote=message)


@simplebot.command(admin=True)
def send(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Send the given payload in the quoted webxdc"""
    quote = message.quote
    if not quote or not is_webxdc(quote.filename):
        replies.add(text=f"❌ Wrong usage", quote=message)
        return

    updates = json.loads(payload)
    if updates and updates[0].get("payload", {}).get("score") is not None:
        scores = {}
        for update in updates:
            payload = update["payload"]
            addr = payload["addr"]
            old_payload = scores.setdefault(addr, update)["payload"]
            if old_payload["score"] < payload["score"]:
                scores[addr] = update
        updates = list(scores.values())
    for update in updates:
        lib.dc_send_webxdc_status_update(
            bot.account._dc_context,
            quote.id,
            as_dc_charpointer(json.dumps(update)),
            as_dc_charpointer("sync"),
        )


def is_webxdc(path: str) -> bool:
    return path.endswith(".xdc")


def get_metadata(path: str) -> dict:
    with ZipFile(path) as xdc:
        with xdc.open("manifest.toml") as manifest:
            meta = toml.loads(manifest.read().decode())
    meta.setdefault("store", {}).setdefault("name", meta["name"])
    for key, key2 in (("version_name", "version_code"), ("author", "author_email")):
        if not meta["store"].get(key) and meta["store"].get(key2):
            meta["store"][key] = meta["store"][key2]
    return meta["store"]


def check_fields(meta: dict) -> bool:
    for field in META_FIELDS:
        if not meta.get(field):
            return False
    return True

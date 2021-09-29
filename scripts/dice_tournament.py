import random
import time
from threading import Thread
from typing import Optional

import simplebot
from simplebot_score import _getdefault  # noqa
from simplebot_score.orm import Base, User, session_scope  # noqa
from sqlalchemy import Column, Float, String

DICES = {
    1: "⚀",
    2: "⚁",
    3: "⚂",
    4: "⚃",
    5: "⚄",
    6: "⚅",
}
TAVERN_COOLDOWN = 60 * 15
BET = 5


class Tavern(Base):
    addr = Column(String(500), primary_key=True)
    join_time = Column(Float, nullable=False)


@simplebot.hookimpl
def deltabot_init(bot: simplebot.DeltaBot) -> None:
    badge = _getdefault(bot, "score_badge", "🎖️")
    desc = f"Probar suerte jugando dados en la taberna, para entrar debes pagar {BET}{badge}"

    bot.commands.register(func=taberna, help=desc)


@simplebot.hookimpl
def deltabot_start(bot: simplebot.DeltaBot) -> None:
    Thread(target=_check_tavern, args=(bot,)).start()


def taberna(bot, message, replies) -> None:
    badge = _getdefault(bot, "score_badge", "🎖️")
    with session_scope() as session:
        user2 = (
            session.query(User)
            .filter_by(addr=message.get_sender_contact().addr)
            .first()
        )
        score = user2.score if user2 else 0
        if score < BET:
            replies.add(
                text=f"❌ No tienes {badge} suficiente para entrar a la taberna",
                quote=message,
            )
            return
        user1 = _get_opponent(user2.addr, session)
        if user1:
            user2.score -= BET
            roll1 = _roll_dice()
            roll2 = _roll_dice()
            while sum(roll1) == sum(roll2):
                roll1 = _roll_dice()
                roll2 = _roll_dice()
            if sum(roll1) < sum(roll2):
                user1, user2 = user2, user1
                roll1, roll2 = roll2, roll1

            user1.score += BET * 2

            text = "🎲 Lanzan los dados sobre la mesa:\n\n"
            text += "{0} {1} ({2})\n{3} {4} ({5})\n\n"
            text += "{0} ganó! y se lleva {6}{7}"
            text = text.format(
                bot.get_contact(user1.addr).name,
                " + ".join(DICES[val] for val in roll1),
                sum(roll1),
                bot.get_contact(user2.addr).name,
                " + ".join(DICES[val] for val in roll2),
                sum(roll2),
                BET * 2,
                badge,
            )
            text += "\n\nTienes: "
            replies.add(
                text=f"{text}{user1.score}{badge}", chat=bot.get_chat(user1.addr)
            )
            replies.add(
                text=f"{text}{user2.score}{badge}", chat=bot.get_chat(user2.addr)
            )
        else:
            chat = bot.get_chat(user2.addr)
            if session.query(Tavern).filter_by(addr=user2.addr).first():
                replies.add(text="❌ Ya estás en la taberna", chat=chat)
            else:
                user2.score -= BET
                player = Tavern(addr=user2.addr, join_time=time.time())
                session.add(player)
                replies.add(
                    text=f"🍺 Entras a la taberna, tomas asiento y saboreas tu bebida mientras esperas en los próximos {TAVERN_COOLDOWN // 60} minutos a que algún oponente aparezca para jugar dados",
                    chat=chat,
                )


def _roll_dice(n=2) -> tuple:
    return tuple(random.randint(1, 6) for _ in range(n))


def _get_opponent(addr: str, session) -> Optional[User]:
    for player in session.query(Tavern):
        if player.addr == addr:
            continue
        session.delete(player)
        return session.query(User).filter_by(addr=player.addr).one()
    return None


def _check_tavern(bot: simplebot.DeltaBot) -> None:
    badge = _getdefault(bot, "score_badge", "🎖️")
    while True:
        try:
            time.sleep(10)
            with session_scope() as session:
                for player in session.query(Tavern):
                    if time.time() - player.join_time > TAVERN_COOLDOWN:
                        user = session.query(User).filter_by(addr=player.addr).one()
                        session.delete(player)
                        user.score += BET
                        bot.get_chat(user.addr).send_text(
                            f"+{BET}{badge} Sales de la taberna sin que nada interesante pase."
                        )
        except Exception as err:
            bot.logger.exception(err)

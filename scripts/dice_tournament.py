import random
import time

import simplebot
import simplebot_score as sc

db: sc.DBManager
DICES = ("⚀", "⚁", "⚂", "⚃", "⚄", "⚅")
MINUTES = 30


@simplebot.hookimpl
def deltabot_init(bot) -> None:
    global db
    db = sc._get_db(bot)
    with db.db:
        db.db.execute(
            """CREATE TABLE IF NOT EXISTS tournament
            (addr TEXT PRIMARY KEY,
            time FLOAT NOT NULL)"""
        )


@simplebot.command
def taberna(bot, message, replies) -> None:
    """Probar suerte jugando dados en la taberna, para entrar debes tener al menos 1🎖"""
    addr = message.get_sender_contact().addr
    score = db.get_score(addr)
    if score < 1:
        replies.add(text="❌ No tienes 🎖(puntos de honor) suficientes para jugar")
        return
    row = _get_opponent(addr)
    if row:
        p1, p2 = row["addr"], addr
        bet = 10 if min((db.get_score(p1), db.get_score(p2))) / 2 > 10 else 1
        roll1 = _roll_dice()
        roll2 = _roll_dice()
        while roll1[1] == roll2[1]:
            roll1 = _roll_dice()
            roll2 = _roll_dice()
        if roll1[1] < roll2[1]:
            p1, p2 = addr, row["addr"]
            roll1, roll2 = roll2, roll1

        p2_score = db.get_score(p2) - bet
        db.set_score(p2, p2_score)
        p1_score = db.get_score(p1) + bet
        db.set_score(p1, p1_score)

        text = "🎲 Lanzan los dados sobre la mesa:\n\n"
        text += "{0} {1} ({2})\n{3} {4} ({5})\n\n"
        text += "{0} ganó! y se lleva {6}🎖 de {3}"
        text = text.format(
            bot.get_contact(p1).name,
            " + ".join(roll1[0]),
            roll1[1],
            bot.get_contact(p2).name,
            " + ".join(roll2[0]),
            roll2[1],
            bet,
        )
        text += "\n\nTienes: {}🎖"
        replies.add(text=text.format(p1_score), chat=bot.get_chat(p1))
        replies.add(text=text.format(p2_score), chat=bot.get_chat(p2))
    else:
        with db.db:
            db.db.execute("REPLACE INTO tournament VALUES (?,?)", (addr, time.time()))
        replies.add(
            text="🍺 Entras a la taberna, tomas asiento y saboreas tu bebida mientras esperas a que algún oponente aparezca para jugar dados en los próximos {} minutos".format(
                MINUTES
            ),
            chat=bot.get_chat(addr),
        )


def _roll_dice():
    dices = []
    total = 0
    for i in range(2):
        rand = random.randrange(0, 6)
        total += rand + 1
        dices.append(DICES[rand])
    return (dices, total)


def _delete_player(addr):
    with db.db:
        db.db.execute("DELETE FROM tournament WHERE addr=?", (addr,))


def _get_opponent(addr):
    q = "SELECT * FROM tournament WHERE addr!=? ORDER BY time DESC"
    for row in db.db.execute(q, (addr,)):
        _delete_player(row["addr"])
        if time.time() - row["time"] > 60 * MINUTES:
            continue
        _delete_player(addr)
        return row

import simplebot
from deltachat import Message
from simplebot.bot import Replies


@simplebot.filter(tryfirst=True)
def filter_messages(message: Message, replies: Replies) -> bool:
    """I will notify you when my encryption key changes."""
    if message.error:
        replies.add(
            text="I was not able to decrypt this message, please repeat.", quote=message
        )
        return True
    return False

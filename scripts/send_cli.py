import simplebot
from simplebot.bot import Replies


@simplebot.hookimpl
def deltabot_init_parser(parser) -> None:
    parser.add_subcommand(send)


class send:
    """send a message to the given address."""

    def add_arguments(self, parser) -> None:
        parser.add_argument("addr", help="email address to send the message to")
        parser.add_argument("--text", help="the message's text body", default=None)
        parser.add_argument("--file", help="path to a file attachment", default=None)

    def run(self, bot, args, out) -> None:
        chat = bot.get_chat(args.addr)
        replies = Replies(bot, bot.logger)
        replies.add(text=args.text, filename=args.file, chat=chat)
        replies.send_reply_messages()
        out.line(f"Message sent.")

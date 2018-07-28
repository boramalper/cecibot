import logging
import json
import os
import sys
import traceback

import redis

import telegram

from updater import start_telegram_updater


def main() -> int:
    logging.basicConfig(format="%(asctime)s  %(levelname)s\t%(message)s", level=logging.INFO)

    start_telegram_updater()

    bot = telegram.Bot(token=os.environ["CECIBOT_TELEGRAM_SECRET"])
    client = redis.StrictRedis()

    logging.info("cecibot-telegram is ready for responses!")

    while True:
        try:
            response = json.loads(client.brpop("telegram_responses")[1])

            if response["kind"] == "error":
                bot.send_message(
                    chat_id=response["opaque"]["chat_id"],
                    text="cecibot error: {}".format(response["error"]["message"]),
                    reply_to_message_id=response["opaque"]["message_id"]
                )
                continue

            bot.send_document(
                chat_id=response["opaque"]["chat_id"],
                document=open(response["file"]["path"], mode="rb"),
                filename=response["file"]["title"] + response["file"]["extension"],  # Undocumented...
                reply_to_message_id=response["opaque"]["message_id"]
            )
            os.unlink(response["file"]["path"])
        except KeyboardInterrupt:
            break

    return os.EX_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except:
        print("UNCAUGHT EXCEPTION!")
        traceback.print_exc()
        sys.exit(os.EX_SOFTWARE)

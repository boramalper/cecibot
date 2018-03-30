import enum
import typing
import json
import sys
import traceback

import redis

import telegram
import telegram.ext as t_ext

import secret

ONLY = 1

COOL_DOWN = 15
MAX_ATTEMPTS = 10


@enum.unique
class RateLimitingStatus(enum.Enum):
    FREE = enum.auto()
    RATE_LIMITED_NOW = enum.auto
    RATE_LIMITED_AGAIN = enum.auto()
    BLACKLISTED = enum.auto()


def main():
    bot = telegram.Bot(token=secret.token)

    updater = t_ext.Updater(secret.token)
    updater.dispatcher.add_handler(t_ext.ConversationHandler(
        entry_points=[
            t_ext.CommandHandler("start", start),
            t_ext.MessageHandler(t_ext.Filters.text, only)
        ],
        states={
            ONLY: [t_ext.MessageHandler(t_ext.Filters.text, only)],
        },
        fallbacks=[t_ext.CommandHandler("cancel", cancel)],
    ))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()

    ####

    client = redis.StrictRedis()
    sub = client.pubsub()

    sub.subscribe("telegramResponses")

    # Ignore (the very first) "subscribe" message
    assert sub.get_message(timeout=None)["type"] == "subscribe"

    print("cecibot-telegram is ready for responses!")

    for response_msg in sub.listen():
        response = json.loads(response_msg["data"])

        if response["kind"] == "file":
            bot.send_document(
                chat_id=response["opaque"]["chat_id"],
                document=open(response["file"]["path"], mode="rb"),
                filename=response["file"]["title"] + response["file"]["extension"],  # Undocumented...
                reply_to_message_id=response["opaque"]["message_id"]
            )
            # TODO
            # os.unlink(request["filePath"])
        elif response["kind"] == "error":
            bot.send_message(
                chat_id=response["opaque"]["chat_id"],
                text="cecibot error: {}".format(response["error"]["message"]),
                reply_to_message_id=response["opaque"]["message_id"]
            )

    sub.unsubscribe()
    sub.close()


def start(bot, update):
    update.message.reply_text("Welcome to the cecibot!")

    return ONLY


def only(bot: telegram.Bot, update: telegram.Update):
    client = redis.StrictRedis()

    if update.message is None or update.message.from_user is None:
        return
    message = update.message

    try:
        rls = rate_limit(client, message.from_user.id)
        if rls == RateLimitingStatus.RATE_LIMITED_NOW:
            message.reply_text("You are trying too fast! Wait for {} seconds...".format(COOL_DOWN))
            message.reply_text("I'll not say no more honey.")
            return
        elif rls != RateLimitingStatus.FREE:
            return

        links = extract_links(message.text, message.entities)

        if len(links) == 0:
            message.reply_text("Send some links!", quote=True)
        elif len(links) > 1:
            message.reply_text("Send links one message at a time!", quote=True)
        else:
            bot.send_chat_action(chat_id=message.chat.id, action=telegram.ChatAction.TYPING)

            n_receivers = client.publish("requests", json.dumps({
                "url": links[0],
                "medium": "telegram",

                "opaque": {
                    "chat_id": message.chat.id,
                    "message_id": message.message_id
                },

                "identifier_version": 1,
                "identifier": {
                    "user_id": message.from_user.id,
                    "chat_id": message.chat.id,
                    "message_id": message.message_id,
                }
            }))

            if n_receivers != 2:
                print("The request is received by other than 2 receivers!")
                print("This might be an indicator that the monitor (or the fetcher) is not working.")
                print("Exiting...")
                sys.exit()
    except:
        traceback.print_exc()

    return ONLY


def cancel(bot, update):
    update.message.reply_text("Sad to see you go!")
    return t_ext.ConversationHandler.END


def error(bot, update, err):
    print("Update `%s` caused error: %s", update, err)


def extract_links(msg: str, entities: typing.List[dict]) -> typing.List[str]:
    links = []
    for entity in entities:
        if entity["type"] != "url":
            continue
        links.append(msg[entity["offset"]: entity["offset"] + entity["length"]])
    return links


def rate_limit(client: redis.StrictRedis, user_id: int) -> RateLimitingStatus:
    counter_name = "telegram.rate_limiting.counter.({})".format(user_id)

    ttl = client.ttl(counter_name)

    # ttl == -1
    # "The key exists but has no associated expire."
    # Meaning, that the e-mail address/domain is blacklisted.
    if ttl == -1:
        return RateLimitingStatus.BLACKLISTED
    # ttl == -2
    # "The key does not exist."
    # Meaning, that the e-mail address/domain is new.
    elif ttl == -2:
        client.setex(counter_name, COOL_DOWN, 0)
        return RateLimitingStatus.FREE
    # ttl >= 0
    # Meaning, tha the e-mail address/domain is (or rather, should be) cooling down.
    # Keep track of their *attempts* and if it exceeds a certain number, blacklist them.
    elif ttl >= 0:
        n_attempts = client.incr(counter_name)

        if n_attempts >= MAX_ATTEMPTS:
            client.set(counter_name, 0)
            return RateLimitingStatus.BLACKLISTED
        elif n_attempts == 1:
            return RateLimitingStatus.RATE_LIMITED_NOW
        else:
            return RateLimitingStatus.RATE_LIMITED_AGAIN


if __name__ == "__main__":
    main()

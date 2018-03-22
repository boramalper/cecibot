import typing
import json

import redis

import telegram
import telegram.ext as t_ext

import secret


ONLY = 1

client = None  # type: redis.StrictRedis


def main():
    global client

    bot = telegram.Bot(token=secret.token)

    updater = t_ext.Updater(secret.token)
    updater.dispatcher.add_handler(t_ext.ConversationHandler(
        entry_points = [ t_ext.CommandHandler("start", start)
                       , t_ext.MessageHandler(t_ext.Filters.text, only)
        ],
        states = {
            ONLY: [t_ext.MessageHandler(t_ext.Filters.text, only)],
        },
        fallbacks = [t_ext.CommandHandler("cancel", cancel)],
    ))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()

    ####

    client = redis.StrictRedis()
    sub    = client.pubsub()

    sub.subscribe("telegramResponses")

    # Ignore (the very first) "subscribe" message
    assert sub.get_message(timeout=None)["type"] == "subscribe"

    print("cecibot-telegram is ready for responses!")

    for response_msg in sub.listen():
        response = json.loads(response_msg["data"])

        if response["kind"] == "file":
            bot.send_document(
                chat_id             = response["opaque"]["chatId"],
                document            = open(response["file"]["path"], mode="rb"),
                filename            = str(response["file"]["title"]),
                reply_to_message_id = response["opaque"]["messageId"]
            )
            # TODO
            # os.unlink(request["filePath"])
        elif response["kind"] == "error":
            bot.send_message(
                chat_id             = response["opaque"]["chatId"],
                text                = "Error: {}".format(response["error"]["message"]),
                reply_to_message_id = response["opaque"]["messageId"]
             )

    sub.unsubscribe()
    sub.close()


def start(bot, update):
    update.message.reply_text("Welcome to the cecibot!")

    return ONLY


def only(bot: telegram.Bot, update: telegram.Update):
    try:
        links = extract_links(update.message.text, update.message.entities)
        print("user said:", update.message.text)

        if len(links) == 0:
            update.message.reply_text("Send some links!", quote=True)
        elif len(links) > 1:
            update.message.reply_text("Send links one message at a time!", quote=True)
        else:
            x = "telegramUserTimer:%d" % (update.effective_user.id,)
            print(x)

            x_ttl = client.ttl(x)
            if x_ttl > 0:
                update.message.reply_text("Cool down! {} seconds left...".format(x_ttl))
                return ONLY

            bot.send_chat_action(chat_id=update.message["chat"]["id"], action=telegram.ChatAction.TYPING)

            client.set(x, "1")
            client.expire(x, 10)

            client.publish("requests", json.dumps({
                "url"   : links[0],
                "medium": "telegram",

                "opaque": {
                    "chatId"   : update.message["chat"]["id"],
                    "messageId": update.message["message_id"]
                },
            }))
    except Exception as e:
        print("EEEE", e)

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
        links.append(msg[entity["offset"] : entity["offset"] + entity["length"]])
    return links


if __name__ == "__main__":
    main()

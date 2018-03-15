"use strict";

const fs = require("fs");

const redis       = require("redis")
    , TelegramBot = require("node-telegram-bot-api")
    ;

const {token} = require("./secrets");


let interrupted = false;

(async () => {
    const bot    = new TelegramBot(token, {polling: true});
    const client = redis.createClient();

    bot.on("polling_error", (error) => {
        console.log("polling error:" );
        console.log(error);  // => 'EFATAL'
    });

    bot.on("webhook_error", (error) => {
        console.log("webhook error: ");  // => 'EPARSE'
        console.log(error);
    });

    client.on("error", function (err) {
        console.log("node_redis error: " + err);
    });

    client.on("connect", function () {
        console.log("node_redis connected!");
    });

    client.on("ready", function () {
        console.log("node_redis ready!");
    });

    // Listen for any kind of message. There are different kinds of
    // messages.
    bot.on("message", (msg) => {
        const chatId = msg.chat.id;
        const links  = linksIn(msg);

        if (links.length === 1) {
            console.log("pushing request for ", links[0]);

            let res = client.lpush("requests", JSON.stringify({
                url   : links[0],
                medium: "telegram",
                opaque: {
                    "chatId": chatId,
                },
            }), function (err, res) {
                console.log("pushed ", err, " ", res);
            });

            bot.sendMessage(chatId, "wait...");
        } else if (links.length > 1) {
            bot.sendMessage(chatId, "Too many URLs!");
        } else {
            bot.sendMessage(chatId, "Send some URLs!");
        }
    });

    loop(bot, client);
})();


function loop(bot, client) {
    if (interrupted) {
        return;
    }

    client.brpop("telegramResponses", 1, function (err, res) {
        if (err === null && res === null) {  // timeout
            loop(bot, client);
            return;
        }

        if (err) {
            console.log("BRPOP err ", err);
            loop(bot, client);
            return;
        }

        const response   = JSON.parse(res[1])
            , filePath   = "/home/bora/labs/cecibot/" + response.fileName + response.fileExtension
            , fileStream = fs.createReadStream(filePath)
            ;

        console.log("sending `" + filePath + "`");
        bot.sendDocument(response.opaque.chatId, fileStream);
        fs.unlink(filePath);

        loop(bot, client);
    });
}


function linksIn(msg) {
    const links = []
        , entities = msg.entities
        ;

    if (entities === undefined) {
        return [];
    }

    for (let entity of entities) {
        if (entity.type === "url") {
            links.push(msg.text.slice(entity.offset, entity.length));
        }
    }

    return links;
}


process.on("SIGINT", function() {
    console.log("Interrupt signal caught, exiting gracefully...");
    interrupted = false;
});

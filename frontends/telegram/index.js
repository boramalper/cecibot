"use strict";

const fs          = require("fs")
    , {promisify} = require("util")
    ;

const redis       = require("redis")
    , TelegramBot = require("node-telegram-bot-api")
    ;

const {token} = require("./secrets");


let interrupted = false;

(async () => {
    const bot    = new TelegramBot(token, {polling: true})
        , pub = redis.createClient()
        , sub = redis.createClient()
        ;

    bot.on("polling_error", (error) => {
        console.log("polling error:" );
        console.log(error);  // => 'EFATAL'
    });

    pub.on("error", function (err) {
        console.log("pub error:", err);
    });

    sub.on("error", function (err) {
        console.log("sub error:", err);
    });


    // Listen for any kind of message. There are different kinds of
    // messages.
    bot.on("message", (msg) => {
        const chatId = msg.chat.id;
        const links  = linksIn(msg);

        if (links.length === 1) {
            console.log("pushing request for", links[0]);

            pub.publish("requests", JSON.stringify({
                url   : links[0],
                medium: "telegram",
                opaque: {
                    "chatId": chatId,
                },
            }));

            bot.sendMessage(chatId, "wait...");
        } else if (links.length > 1) {
            bot.sendMessage(chatId, "Too many URLs!");
        } else {
            bot.sendMessage(chatId, "Send some URLs!");
        }
    });

    sub.on("message", async function _ (channel, message) {
        console.log("message:", channel, message);

        const response = JSON.parse(message)
            , filePath   = "/home/bora/labs/cecibot/" + response.fileName + response.fileExtension
            , fileStream = fs.createReadStream(filePath)
        ;

        bot.sendDocument(response.opaque.chatId, fileStream, {}, {
            contentType: response.fileMIME,
        });
        fs.unlink(filePath);
    });

    sub.subscribe("telegramResponses");
})();


function linksIn(msg) {
    const links    = []
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

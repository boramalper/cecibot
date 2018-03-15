"use strict";

const crypto      = require("crypto")
    , {promisify} = require("util")
    ;

const puppeteer = require("puppeteer")
    , redis     = require("redis")
    ;

let notInterrupted = true;

(async () => {
    const browser = await puppeteer.launch({args: ["--no-sandbox", "--disable-setuid-sandbox"]})
        , client  = redis.createClient()
        ;

    const brpop = promisify(client.brpop).bind(client)
        , lpush = promisify(client.lpush).bind(client)
        ;

    client.on("error", function (err) {
        console.log("node_redis error: " + err);
    });

    while (notInterrupted) {
        console.log("waiting for requests...");
        const [_, requestJSON] = await brpop("requests", 0)
            ,     request      = JSON.parse(requestJSON)
            ;
        console.log(request);

        const [fileName, error] = await getPDF(browser, request.url);
        if (error) {
            console.log("ERROR: ", error);
            continue;
        }

        lpush(request.medium + "Responses", JSON.stringify({
            respondedOn  : Math.trunc(Date.now() / 1000),  // UNIX Time (seconds)
            type         : "file",
            fileName     : fileName,
            fileExtension: ".pdf",
            fileMIME     : "application/pdf",
            opaque       : request.opaque,
        }));
    }

    await browser.close();
})();


process.on("SIGINT", function() {
    console.log("Interrupt signal caught, exiting gracefully...");
    notInterrupted = false;
});


async function getJPG(browser, url) {
    const page = await visit(browser, url);
    const name = randomName();

    await page.screenshot({
        path: name + ".jpg",
        fullPage: true,
        quality: 70,
    });

    return name;
}


async function getPDF(browser, url) {
    const [page, error] = await visit(browser, url);
    if (error) {
        return [null, error];
    }
    const name = randomName();

    // Generates a PDF with "screen" media type.
    await page.emulateMedia("screen");
    await page.pdf({
        path: name + ".pdf",
        // Width & Height will be swapper because of the landscape (orientation)!
        landscape: true,
        width: "1080px",
        height: "1920px",
    });

    return [name, null];
}

async function visit(browser, url) { // return a [page + goto, error]
    const page = await browser.newPage();

    try {
        await page.goto(url, {
            // Maximum navigation time in milliseconds (* 1000).
            timeout: 20 * 1000,
            // Consider navigation to be finished when there are no more than 2 network connections for at least 500 ms.
            waitUntil: "networkidle2",
        });
    } catch (error) {
        return [null, error];
    }

    return [page, null];
}

function randomName() {
    return crypto.randomBytes(16).toString("hex");
}

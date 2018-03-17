"use strict";

const crypto      = require("crypto")
    , {promisify} = require("util")
    ;

const puppeteer   = require("puppeteer")
    , redis       = require("redis")
    ;

let notInterrupted = true;

(async () => {
    const browser = await puppeteer.launch()
        , sub     = redis.createClient()
        , pub     = redis.createClient()
        ;

    sub.on("error", function (err) {
        console.log("sub (redis) error: " + err);
    });
    pub.on("error", function (err) {
        console.log("pub (redis) error: " + err);
    });

    sub.on("message", async function _ (channel, message) {
        console.log("sub channel " + channel + ": " + message);
        const request = JSON.parse(message);

        const [page, visitError] = await visit(browser, request.url);
        if (visitError) {
            console.log("visit error: ", visitError);
            return;
        }
        console.log("visited!");

        const pdfName = await getPDF(page);
        console.log("got PDF!!", pdfName);

        pub.publish(request.medium + "Responses", JSON.stringify({
            respondedOn: Math.trunc(Date.now() / 1000),  // UNIX Time (seconds)
            type: "file",
            title: await page.title(),
            fileName: pdfName,
            fileExtension: ".pdf",
            fileMIME: "application/pdf",
            opaque: request.opaque,
        }));
        console.log("pushed!\n");
        await page.close();
    });

    sub.subscribe("requests");
})();


process.on("SIGINT", function() {
    console.log("Interrupt signal caught, exiting gracefully...");
    notInterrupted = false;
});


async function getPDF(page) {
    const name = randomName();

    // Generates a PDF with "screen" media type.
    await page.emulateMedia("screen");

    let height = await page.evaluate(() => document.documentElement.scrollHeight);
    console.log("height:", height);

    await page.pdf({
        path: name + ".pdf",
        width: "1080px",
        height: height+1 + "px",  // +1 to prevent the last empty page
    });

    return name;
}


async function visit(browser, url) { // return a [page + goto, error]
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on("request", request => {
        if (["document", "stylesheet", "image", "font"].includes(request.resourceType()))
            request.continue();
        else
            request.abort();
    });

    try {
        await page.goto(url, {
            // Maximum navigation time in milliseconds (* 1000).
            timeout: 5 * 1000,
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

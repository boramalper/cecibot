"use strict";

const crypto      = require("crypto")
    , fs          = require("fs")
    , path        = require("path")
    , {URL}       = require("url")
    , {promisify} = require("util")
    ;

const puppeteer       = require("puppeteer")
    , redis           = require("redis")
    , request_promise = require("request-promise-native")
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

        if (isFile(request.url)) {
            console.log("that's a file!");
            const [err, fileName] = await downloadFile(request.url);
            if (err) {
                console.log("download err:", err);
            } else {
                pub.publish(request.medium + "Responses", JSON.stringify({
                    respondedOn: Math.trunc(Date.now() / 1000),  // UNIX Time (seconds)
                    title: undefined,
                    fileName: fileName,
                    fileMIME: "application/octet-stream",
                    opaque: request.opaque,
                }));
                console.log("pushed " + fileName + "!\n");
            }
        } else {
            const [title, pdfName] = await getPDF(browser, request.url);
            pub.publish(request.medium + "Responses", JSON.stringify({
                respondedOn: Math.trunc(Date.now() / 1000),  // UNIX Time (seconds)
                title: title,
                fileName: pdfName,
                fileMIME: "application/pdf",
                opaque: request.opaque,
            }));
            console.log("pushed " + pdfName + "!\n");
        }
    });

    sub.subscribe("requests");
})();


process.on("SIGINT", function() {
    console.log("Interrupt signal caught, exiting gracefully...");
    notInterrupted = false;
});


async function downloadFile(url) {
    let error;

    /* JavaScript, and it's ecosystem is *idiotic*:

    I, and seemingly many others as well, spent an hour trying to figure out why I cannot GET (download) files as they
    are, only to realise -much to my surprise- that request library returns an UTF-8 encoded string.

    https://stackoverflow.com/questions/14855015/getting-binary-content-in-node-js-using-request

    There is not a single f**king mention of this fact in their documentation, yet alone of the `encoding` field in
    `options`.

    Might as well be our fault to expect anything else from those encode all their binary data in base64.
    */
    const r = await request_promise(url, {encoding: null}).on("response", function(response) {
            if (response.statusCode !== 200) {
                error = "HTTP status code: " + response.statusCode;
            } else if (response.headers["content-length"] > 5 * 1024 * 1024) {
                error = "Content too big: " + response.headers["content-length"] + " bytes";
            }
        });

    if (error)
        return [error, null];

    const {pathname} = new URL(url)
        , path_      = path.parse(pathname)
        , fileName   = randomName() + path_.ext
        , fsws       = fs.createWriteStream(fileName, {
            flags: "w",
        })
        , write      = promisify(fsws.write).bind(fsws)
        , close      = promisify(fsws.close).bind(fsws)
        ;

    await write(Buffer.from(r, "binary"));
    await close();

    return [null, fileName];

}


function isFile(url_s) {
    const {pathname} = new URL(url_s)
        , path_      = path.parse(pathname)
        ;

    // pageExtensions is the list of common web-page extensions that should be "visited" by the browser.
    // https://stackoverflow.com/questions/1614520/what-are-common-file-extensions-for-web-programming-languages
    const pageExtensions = [
        ".asp",
        ".aspx",
        ".asx",
        ".cfm",
        ".yaws",
        ".htm",
        ".html",
        ".xhtml",
        ".jhtml",
        ".jsp",
        ".jspx",
        ".pl",
        ".py",
        ".rb",
        ".rhtml",
        ".shtml",
        ".cgi"
    ];

    return path_.ext !== "" && !pageExtensions.includes(path_.ext);
}


async function getPDF(browser, url) {
    const [page, visitError] = await visit(browser, url);
    if (visitError) {
        console.log("visit error: ", visitError);
        return;
    }

    const fileName   = randomName() + ".pdf"
        , title  = page.title()
        , height = await page.evaluate(() => document.documentElement.scrollHeight)
        ;

    await page.emulateMedia("screen");  // Generates a PDF with "screen" media type.
    await page.pdf({
        path: fileName,
        width: "1080px",
        height: height + 32 + "px",  // + 32 to prevent the last empty page (safety margin)
    });
    await page.close();

    return [title, fileName];
}


async function visit(browser, url) { // return a [page + goto, error]
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on("request", request => {
        if (["document", "stylesheet", "image", "font"].includes(request.resourceType()))
            request.continue();
        else {
            console.log("request is aborted:", request);
            request.abort();
        }
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

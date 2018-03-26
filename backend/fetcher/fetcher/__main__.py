from typing import *

import asyncio
import uuid
import urllib.parse as u_parse
import json
import os.path as o_path

import pyppeteer
import pyppeteer.browser as p_browser
import pyppeteer.errors as p_errors
import pyppeteer.page as p_page
import pyppeteer.network_manager as p_network_manager

import redis

import requests

# =============
# CONFIGURATION
# =============
DOWNLOAD_PATH = "/tmp"
MAX_FILE_SIZE = 2 * 1024 * 1024


# =============


async def main():
    browser = await pyppeteer.launch()

    client = redis.StrictRedis()
    sub = client.pubsub()

    sub.subscribe("requests")

    # Ignore (the very first) "subscribe" message
    assert sub.get_message(timeout=None)["type"] == "subscribe"

    print("cecibot-backend is ready for requests!")

    for requestMsg in sub.listen():
        request = json.loads(requestMsg["data"])

        try:
            response = await processRequest(browser, request)
        except:
            response = {
                "kind": "error",

                "error": {
                    "message": "cecibot: internal error",
                },
            }

        response["opaque"] = request["opaque"]
        client.publish("{}Responses".format(request["medium"]), json.dumps(response))

    sub.unsubscribe()
    sub.close()

    await browser.close()


async def processRequest(browser: p_browser.Browser, request: Dict[str, Any]) -> Dict[str, Any]:
    if isFile(request["url"]):
        try:
            filePath, fileMIME = downloadFile(request["url"])
        except Error as err:
            response = {
                "kind": "error",

                "error": {
                    "message": err.message,
                },
            }
        else:
            print("%s is downloaded at `%s`" % (request["url"], filePath))
            response = {
                "kind": "file",

                "file": {
                    "title": None,
                    "path": filePath,
                    "extension": urlExtension(request["url"]),
                    "mime": fileMIME,
                    "size": o_path.getsize(filePath),
                },
            }
    else:
        try:
            page = await visit(browser, request["url"])
        except Error as err:
            response = {
                "kind": "error",

                "error": {
                    "message": err.message,
                },
            }
        else:
            filePath = await getPDF(page)
            size = o_path.getsize(filePath)

            if size > MAX_FILE_SIZE:
                response = {
                    "kind": "error",

                    "error": {
                        "message": "file is too big: {} bytes (> {} bytes of maximum allowed)".format(size, MAX_FILE_SIZE)
                    }
                }
            else:
                print("%s is saved at `%s`" % (request["url"], filePath))

                response = {
                    "kind": "file",

                    "file": {
                        "title": await page.title(),
                        "path": filePath,
                        "extension": ".pdf",
                        "mime": "application/pdf",
                        "size": size,
                    },
                }

            await page.close()

    return response


def downloadFile(url: str) -> Tuple[str, str]:
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        raise Error("not 200 OK: {}", r.status_code)

    if "content-length" not in r.headers:
        raise Error("file size unknown: \"content-length\" header is missing")

    if int(r.headers["content-length"]) > MAX_FILE_SIZE:
        raise Error("file is too big: {} bytes (> {} bytes of maximum allowed)", r.headers["content-length"],
                    MAX_FILE_SIZE)

    filePath = o_path.join(DOWNLOAD_PATH, str(uuid.uuid4()) + urlExtension(url))
    with open(filePath, "wb") as f:
        f.write(r.content)

    return filePath, r.headers["content-type"]


async def getPDF(page: p_page.Page) -> str:
    filePath = o_path.join(DOWNLOAD_PATH, str(uuid.uuid4()) + ".pdf")
    height = await page.evaluate("document.documentElement.scrollHeight", force_expr=True)

    await page.emulateMedia("screen")
    await page.pdf({
        "path": filePath,
        "width": "1080px",
        "height": str(height + 32) + "px"  # + 32 to prevent the last empty page (safety margin)
    })

    return filePath


async def visit(browser: p_browser.Browser, url: str) -> p_page.Page:
    page = await browser.newPage()
    await page.setJavaScriptEnabled(False)
    await page.setExtraHTTPHeaders({"DNT": "1"})  # Do Not Track (DNT)
    await page.setRequestInterception(True)

    @page.on("request")
    async def _(request: p_network_manager.Request):
        if request.resourceType in ["document", "stylesheet", "image", "font"]:
            await request.continue_()
        else:
            await request.abort()

    try:
        await page.goto(url, {
            # Maximum navigation time in milliseconds (* 1000):
            "timeout": 5 * 1000,
            # Consider navigation to be finished when there are no more than 2 network connections for at least 500 ms:
            "waitUntil": "networkidle2",
        })
    except p_errors.TimeoutError:
        await page.close()
        raise Error("timeout")
    except p_errors.PageError as exc:
        await page.close()
        raise Error("navigation: {}", exc.args[0])  # e.g. "net::ERR_NAME_NOT_RESOLVED"

    return page


def urlExtension(url: str) -> str:
    return o_path.splitext(u_parse.urlparse(url).path)[1]


def isFile(url: str) -> bool:
    # pageExtensions is the list of common web-page extensions that should be "visited" by the browser.
    # https://stackoverflow.com/questions/1614520/what-are-common-file-extensions-for-web-programming-languages
    pageExtensions = [
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
    ]

    uext = urlExtension(url)
    return uext and uext not in pageExtensions


class Error(Exception):
    message: str
    debug_dict: Optional[Dict[str, Any]]

    def __init__(self, fmt: str, *args: Any, debug_dict: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.message = fmt.format(*args)
        self.debug_dict = debug_dict

        if self.debug_dict is not None:
            print("Error:")
            print(debug_dict)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

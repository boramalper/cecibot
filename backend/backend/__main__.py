from typing import *

import asyncio
import logging
import uuid
import urllib.parse as u_parse
import json
import os.path as o_path
import sys
import traceback

import os
import pyppeteer
import pyppeteer.browser as p_browser
import pyppeteer.errors as p_errors
import pyppeteer.page as p_page
import pyppeteer.network_manager as p_network_manager

import redis

import requests

from request_logger import RequestLogger

# =============
# CONFIGURATION
# =============
DOWNLOAD_PATH = "/tmp"
MAX_FILE_SIZE = 2 * 1024 * 1024
# =============


async def main() -> int:
    logging.basicConfig(format="%(asctime)s  %(levelname)s\t%(message)s", level=logging.INFO)

    try:
        request_logger = RequestLogger()
    except:
        traceback.print_exc()
        return 1

    client = redis.StrictRedis()
    browser = await pyppeteer.launch()

    logging.info("cecibot-backend is ready for requests!")

    try:
        while True:
            request = json.loads(client.brpop("requests")[1])

            request_logger.log(
                request["url"],
                request["medium"],
                int(request["identifier_version"]),
                request["identifier"]
            )

            try:
                response = await processRequest(browser, request)
            except Error as err:
                response = {
                    "kind": "error",

                    "error": {
                        "message": err.message,
                    },
                }

            response["opaque"] = request["opaque"]
            response["url"] = request["url"]
            client.lpush("{}_responses".format(request["medium"]), json.dumps(response))
    except KeyboardInterrupt:
        return 0
    finally:
        await browser.close()


async def processRequest(browser: p_browser.Browser, request: Dict[str, Any]) -> Dict[str, Any]:
    if isFile(request["url"]):
        filePath, fileMIME = downloadFile(request["url"])
        response = {
            "kind": "file",

            "file": {
                "title": urlBasename(request["url"]),
                "path": filePath,
                "extension": urlExtension(request["url"]),
                "mime": fileMIME,
                "size": o_path.getsize(filePath),
            },
        }
    else:
        page = await visit(browser, request["url"])
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
    try:
        r = requests.get(url, stream=True)
    except requests.exceptions.InvalidURL:
        raise Error("invalid URL!")
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

    try:
        """
        You are not alone:
        
        > At the risk of spamming, I'm going to post this again, so we can stay on top of the actual issue:
        >
        > The underlying problem is that there is a race condition between the event that clears execution contexts and
        > the event that adds new execution contexts.
        >
        > When you navigate to a new page, sometimes headless chrome will add the new contexts, before clearing the old
        > ones. When it goes to clear the contexts, it blows away the recently added context, causing: Cannot find
        > context with specified id undefined.
        >
        > I think the fix should come from upstream, since I think it's going to be quite difficult to handle correctly
        > in puppeteer.
        https://github.com/GoogleChrome/puppeteer/issues/1325#issuecomment-366254084

        Also: https://github.com/boramalper/cecibot/issues/2
        """
        height = await page.evaluate("document.documentElement.scrollHeight", force_expr=True)
    except pyppeteer.errors.NetworkError:
        # Even though the PDF we are creating is no longer full-height (i.e. has a height equal to the height of the
        # web-page), we can still create a PDF instead of failing.
        height = 1920

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
    async def _(request: p_network_manager.Request) -> None:
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


def urlBasename(url: str) -> str:
    return o_path.basename(u_parse.urlparse(url).path)


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

    def __init__(self, fmt: str, *args: Any, **debug_dict: Optional[Dict[str, Any]]):
        super().__init__()
        self.message = fmt.format(*args)
        self.debug_dict = debug_dict

        if self.debug_dict:
            logging.debug("Debugging Info:")
            for k, v in debug_dict.items():
                logging.debug("{}\t{}".format(k, v))


if __name__ == "__main__":
    try:
        sys.exit(asyncio.get_event_loop().run_until_complete(main()))
    except:
        print("UNCAUGHT EXCEPTION!")
        traceback.print_exc()
        sys.exit(os.EX_SOFTWARE)


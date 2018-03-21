from typing import *

import asyncio
import uuid
import urllib.parse as u_parse
import json
import time
import math
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
MAX_FILE_SIZE = 5 * 1024 * 1024
# =============


error = str


async def main():
    browser = await pyppeteer.launch()

    client = redis.StrictRedis()
    sub    = client.pubsub()

    sub.subscribe("requests")

    for requestMsg in sub.listen():
        print(requestMsg)
        if requestMsg["type"] == "subscribe":
            continue

        request    = json.loads(requestMsg["data"])
        print(request)

        if isFile(request["url"]):
            r = downloadFile(request["url"])
            if type(r) is error:
                print(r)
                continue
            else:
                filePath, fileMIME = r

            print("%s is downloaded at `%s`" % (request["url"], filePath))

            response = {
                "title": None,
                "respondedOn": math.trunc(time.time()),
                # "completed"    : false,                            # Whether the page timed out or not.
                "filePath": filePath,
                "fileExtension": urlExtension(request["url"]),
                "fileMIME": fileMIME,
                "fileSize": o_path.getsize(filePath),
            }
        else:
            page = await visit(browser, request["url"])
            if type(page) is error:
                print(page)
                continue
            filePath = await getPDF(page)
            print("%s is saved at `%s`" % (request["url"], filePath))
            response = {
                "title"        : await page.title(),
                "respondedOn"  : math.trunc(time.time()),
                # "completed"    : false,                            # Whether the page timed out or not.
                "filePath"     : filePath,
                "fileExtension": ".pdf",
                "fileMIME"     : "application/pdf",
                "fileSize"     : o_path.getsize(filePath),
            }
            await page.close()

        response["opaque"] = request["opaque"]
        client.publish(request["medium"] + "Responses", json.dumps(response))

    sub.unsubscribe()
    sub.close()

    await browser.close()


def downloadFile(url: str) -> Union[error, Tuple[str, str]]:
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        return "failure! %d" % (r.status_code,)

    if "content-length" not in r.headers:
        return "file size unknown!"

    if int(r.headers["content-length"]) > MAX_FILE_SIZE:
        return "file is too big: %d bytes" % (r.headers["content-length"],)

    filePath = o_path.join(DOWNLOAD_PATH, str(uuid.uuid4()) + urlExtension(url))
    with open(filePath, "wb") as f:
        f.write(r.content)

    return filePath, r.headers["content-type"]


async def getPDF(page: p_page.Page) -> str:
    filePath = o_path.join(DOWNLOAD_PATH, str(uuid.uuid4()) + ".pdf")
    height   = await page.evaluate("document.documentElement.scrollHeight", force_expr=True)

    await page.emulateMedia("screen")
    await page.pdf({
        "path"  : filePath,
        "width" : "1080px",
        "height": str(height + 32) + "px"  # + 32 to prevent the last empty page (safety margin)
    })

    return filePath


async def visit(browser: p_browser.Browser, url: str) -> Union[error, p_page.Page]:
    page = await browser.newPage()
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
        return "timeout!"

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


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

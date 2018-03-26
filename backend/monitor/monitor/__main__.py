import json
import sqlite3

import redis


def main():
    client = redis.StrictRedis()
    sub    = client.pubsub()

    sub.subscribe("requests")

    # Ignore (the very first) "subscribe" message
    assert sub.get_message(timeout=None)["type"] == "subscribe"

    print("cecibot-monitor is ready for requests!")

    for requestMsg in sub.listen():
        request = json.loads(requestMsg["data"])


def setup_database() -> sqlite3.Connection:
    conn = sqlite3.connect("d")





if __name__ == "__main__":
    main()

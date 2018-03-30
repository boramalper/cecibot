import datetime
import logging
import json
import sqlite3
import os.path
import time
import sys

import redis

# =============
# CONFIGURATION
# =============
now = datetime.datetime.utcnow()
DATABASE_PATH = os.path.expanduser("~/.cecibot/monitor/requests_{YEAR}-{MONTH}.sqlite3".format(YEAR=now.year, MONTH=now.month))
# =============


def main():
    global DATABASE_PATH

    logging.basicConfig(format="%(asctime)s  %(message)s", level=logging.INFO)

    try:
        conn = setup_database(DATABASE_PATH)
    except:
        logging.exception("Could NOT setup database!")
        sys.exit(1)
    else:
        logging.info("Connected to the database.")

    client = redis.StrictRedis()
    sub = client.pubsub()

    sub.subscribe("requests")

    # Ignore (the very first) "subscribe" message
    assert sub.get_message(timeout=None)["type"] == "subscribe"

    logging.info("Ready for requests.")

    try:
        for requestMsg in sub.listen():
            try:
                request = json.loads(requestMsg["data"])
            except json.JSONDecodeError:
                logging.exception("Could NOT decode \"data\" from \"requests\" channel!")
                sys.exit(1)

            print("URL:", request["url"])

            try:
                conn.execute(
                    "INSERT INTO request (url, medium, identifier_version, identifier) VALUES (?, ?, ?, ?);", (
                    request["url"], request["medium"], request["identifier_version"], json.dumps(request["identifier"])
                ))
            except:
                logging.exception("Could NOT insert the request into the database!")
                sys.exit(1)
    except KeyboardInterrupt:
        conn.close()
        sys.exit(0)


def setup_database(path) -> sqlite3.Connection:
    LATEST_VERSION = 1

    conn = sqlite3.connect(path, isolation_level=None)

    def user_version() -> int:
        return conn.execute("PRAGMA USER_VERSION;").fetchone()[0]

    cur = conn.cursor()
    cur.execute("BEGIN;")
    try:
        while user_version() < LATEST_VERSION:
            """
            Beneath lies the code that upgrades the database schema from one version to another.
            
            If a top-level (i.e. `user_version() == X`) if-statement is marked as `# FROZEN`, do NOT alter it!
            
            If you'd like to change something, try upgrading the `user_version` and migrate to the new schema; if the
            changes you are requesting is not possible by a database migration -whatever it might be- consider the new
            database as entirely new, and develop a tool to import data from the current database to the new one.
            """

            # FROZEN
            if user_version() == 0:
                logging.info("Initialising the database for the first time...")
                conn.execute("""
                    CREATE TABLE request (
                      -- id is just an integer primary key:
                        id                 INTEGER NOT NULL PRIMARY KEY
                      
                      -- The UNIX Time request is received __by the monitor__: 
                      , received_on        INTEGER NOT NULL CHECK (received_on >= {}) DEFAULT (cast(strftime('%s', 'now') as int))
                      
                      -- The requested URL
                      -- A URL is assumed to have at minimum 7 characters:
                      --   ftp://x
                      -- * +3 for the scheme
                      -- * +3 for `://`
                      -- * +1 for the host
                      , url                TEXT    NOT NULL CHECK (length(url) >= 7)
                      
                      -- The medium through which the request is received:
                      , medium             TEXT    NOT NULL CHECK (length(medium) > 0) COLLATE NOCASE
                      
                      -- The version number of the identifier (see below)
                      , identifier_version INTEGER NOT NULL CHECK (identifier_version > 0)
                      
                      -- All the necessary info encoded in JSON to __uniquely identify__
                      --   A. The Sender
                      --   B. The Message
                      -- of the request made, given a medium.
                      --
                      -- Identifiers must supply a version number (again, tied to the medium; see `identifier_version`
                      -- column) to version the changes in their schema.
                      --
                      -- Example:
                      --
                      -- {{ "chatId": 76868987
                      -- , "messageId: 8754
                      -- }}
                      -- (double curly braces is to escape str.format())
                      , identifier         TEXT    NOT NULL CHECK (length(identifier) > 0)
                    );
                """.format(int(time.time())))
                conn.execute("CREATE INDEX received_on__idx ON request (received_on ASC);")
                conn.execute("CREATE INDEX medium__identifier_version__idx ON request (medium, identifier_version);")
                conn.execute("PRAGMA USER_VERSION = 1;")

        cur.execute("COMMIT;")
    except conn.Error:
        cur.execute("ROLLBACK;")
        raise

    return conn


if __name__ == "__main__":
    main()

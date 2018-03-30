from typing import *

import datetime
import logging
import sqlite3
import os.path
import time


now = datetime.datetime.utcnow()

# =============
# CONFIGURATION
# =============
MAX_BUFF_SIZE = 20
DATABASE_PATH = os.path.expanduser("~/.cecibot/monitor/requests_{YEAR}-{MONTH}.sqlite3".format(YEAR=now.year, MONTH=now.month))
# =============


class RequestLogger:
    LATEST_USER_VERSION = 1

    def __init__(self, path: str = DATABASE_PATH) -> None:
        self._conn = self._setup_database(path)
        self._buff = []

    def log(self, url: str, medium: str, identifier_version: int, identifier: str) -> None:
        self._buff.append((url, medium, identifier_version, identifier))

        if len(self._buff) >= MAX_BUFF_SIZE:
            self._flush()

    def _flush(self) -> None:
        self._conn.executemany(
            "INSERT INTO request (url, medium, identifier_version, identifier) VALUES (?, ?, ?, ?);",
            self._buff
        )

    @classmethod
    def _setup_database(cls, path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(path, isolation_level=None)

        def user_version() -> int:
            return conn.execute("PRAGMA USER_VERSION;").fetchone()[0]

        cur = conn.cursor()
        cur.execute("BEGIN;")
        try:
            while user_version() < cls.LATEST_USER_VERSION:
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
                    conn.execute(
                        "CREATE INDEX medium__identifier_version__idx ON request (medium, identifier_version);")
                    conn.execute("PRAGMA USER_VERSION = 1;")

            cur.execute("COMMIT;")
        except conn.Error:
            cur.execute("ROLLBACK;")
            raise

        return conn

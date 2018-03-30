# cecibot - Design

- Files are saved at `~/.cecibot/dropbox/`
- Request log is at `~/.cecibot/monitor/requests.sqlite3`

## redis

### Keys
- Programs must *prefix* the keys they create with their short name:
  
  __For instance:__
  - `cecibot-email` -> `email.something`
  - `cecibot-telegram` -> `telegram.something`
  
  and so on. See the documentation at the their directory for further details.

### Channels
- `requests` channel
  - Each message is JSON-encoded with the following schema:

    ```
    {
        "url"       : "https://tr.wikipedia.org/wiki/Anasayfa",
        "medium"    : "telegram"  # camelCase.

        # opaque is meant for the frontend, pass it in the response just as it
        # is provided in the request
        "opaque"    : {
        	"chatID": 1212121  # For Telegram
        }
        
        # identifier
        "identifier": {
            "chatID"  : 1212121,
            "messageId: 8754
        }
    }
    ```

- `{MEDIUM}Responses` channel
  - `MEDIUM`s:
    - `email`
    - `telegram`
    - `messenger`
  - Each message is JSON-encoded with the following schema:

    ```
    {
        "kind": "file",
        "url" : "https://tr.wikipedia.org/",

        "file": {
            "title"    : "Vikipedi: Özgür Ansiklopedi",
            "path"     : "3d0738a4421f3c4be882068ca422a8a1",
            "extension": ".pdf",
            "mime"     : "application/pdf",
            "size"     : 16777216
        },

        # opaque is meant for the frontend, pass it in the response just as it
        # is provided in the request
        "opaque": {
            "chatID": 1212121  # For Telegram
        }
    }

    OR

    {
        "kind"       : "error",
        "url" : "https://tr.wikipedia.org/",

        "error": {
            "message": "error message here!"
        },

        # opaque is meant for the frontend, pass it in the response just as it
        # is provided in the request
        "opaque": {
            "chatID": 1212121,  # For Telegram
        }
    }
    ```


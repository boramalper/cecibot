# cecibot - Design

## redis

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


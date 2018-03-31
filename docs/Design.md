# cecibot - Design

- Request log is at `~/.cecibot/backend/requests.sqlite3`

## redis

### `requests`

- `requests` is a FIFO queue implemented as a list:
  - `LPUSH` & `BRPOP`
  - `LTRIM` if you want to fix its length
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
        
        # identifier must contain all the necessary info to __uniquely identify__
        #
        # A. The Sender
        # B. The Message
        #
        # of the request made, given a medium.
        #
        # Identifiers must supply a version number > 0 (again, tied to the medium;
        # see `identifier_version`) to version the changes in their schema.
        "identifier_version": 1,
        "identifier": {
            "chatID"  : 1212121,
            "messageId: 8754
        }
    }
    ```
  


### `{MEDIUM}_responses`

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
      "kind": "error",
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



### Other
- Programs must *prefix* the keys they create with their short name:
  
  __For instance:__
  - `cecibot-email` -> `email.something`
  - `cecibot-telegram` -> `telegram.something`
  
  and so on. See the documentation at the their directory for further details.

  

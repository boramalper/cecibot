# cecibot - Design

## redis

- `requests` channel
  - Each message is JSON-encoded with the following schema:

    ```
    {
        "receivedOn": 878657890,  // UNIX Time.
        "url"       : "https://tr.wikipedia.org/wiki/Anasayfa",
        "medium"    : "telegram"  // camelCase.
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
        "title"        : "Vikipedi: Özgür Ansiklopedi",    // <title> of the webpage.
        "respondedOn"  : 45677543,                         // UNIX Time.
        "completed"    : false,                            // Whether the page timed out or not.
        "fileName"     : "3d0738a4421f3c4be882068ca422a8a1",
        "fileExtension": ".pdf",
        "fileMIME"     : "application/pdf",
        // opaque is meant for the frontend, pass it in the response just as it
        // is provided in the request
        "opaque": {
        	"chatID": 1212121,  // For Telegram
        }
    }
    ```

# cecibot-monitor

## Database Design

### user_version = 1
```sql
CREATE TABLE request (
  -- id is just an integer primary key:
    id          INTEGER NOT NULL PRIMARY KEY
  
  -- The UNIX Time request is received __by the monitor__: 
  , received_on INTEGER NOT NULL CHECK (received_on > 0)
  
  -- The requested URL
  , url         TEXT    NOT NULL CHECK (length(url) > 0)
  
  -- The medium through which the request is received:
  , medium      TEXT    NOT NULL CHECK (length(medium) > 0)
  
  -- All the necessary info encoded in JSON to __uniquely identify__
  --   A. The Sender
  --   B. The Message
  -- of the request made, given a medium.
  --
  -- Identifiers must contain a version number (again, tied to the medium) to
  -- version the changes in their schema.
  --
  -- Example:
  --
  -- { "version": "0.1.0"
  -- 
  -- , "chatId": 76868987
  -- , "messageId: 8754
  -- }
  , identifier  TEXT    NOT NULL CHECK (length(identifier) > 0)
); 
```

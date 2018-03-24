from typing import *

import email
import email.message
import email.policy
from email.header import decode_header
import json
import re

import boto3


def main():
    sqs = boto3.resource("sqs")

    queue = sqs.get_queue_by_name(QueueName="cecibot-request-bot")  # type: boto3.sqs.Queue

    while True:
        # https://boto3.readthedocs.io/en/latest/reference/services/sqs.html?highlight=get_queue_by_name#SQS.Queue.receive_messages
        messages = queue.receive_messages(WaitTimeSeconds=2)
        if not messages:
            print("no messages received in 20 seconds!")
            break  # TODO: continue

        for message in messages:
            body = json.loads(message.body)
            mail = Mail.from_string(json.loads(body["Message"])["content"])

            print("From   :", mail.from_)
            print("Subject:", mail.subject)
            print(mail.body)
            print()
            print()


class Mail:
    from_  : (str, str)  # (e-mail address, name)
    subject: str
    body   : str

    def __init__(self):
        self.from_   = None
        self.subject = None
        self.body    = None

    @classmethod
    def from_string(cls, s: str) -> "Mail":
        self = cls()
        msg = email.message_from_string(s, policy=email.policy.default)

        self.from_   = self._get_from(msg)
        self.subject = self._get_subject(msg)
        self.body    = self._get_body(msg)

        return self

    @staticmethod
    def _get_from(msg: email.message.EmailMessage) -> (str, Optional[str]):
        # RegEx:
        # The (very simplistic) assumption is that "From:" field is:
        #   1. Either
        #      `Name Surname <name@email.com>`
        #   2. Or
        #      `name@email.com`
        #
        # And we accept any string that has an '@' in it as an e-mail address.
        r = re.compile(r"(?:(.*) <(.+@.+)>)|(.+@.+)")
        m = r.findall(msg["from"])[0]
        if m[0] and m[1]:
            return m[1], m[0]
        elif m[3]:
            return m[3]
        else:
            raise Exception("from couldn't be parsed!")

    @staticmethod
    def _get_subject(msg: email.message.EmailMessage) -> str:
        subject_bytes, subject_encoding = decode_header(msg["subject"])[0]
        if subject_encoding:
            return subject_bytes.decode(subject_encoding)
        else:
            return subject_bytes

    @staticmethod
    def _get_body(msg: email.message.EmailMessage) -> Optional[str]:
        candidate = None

        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.is_multipart() and part.get(
                    "Content-Disposition") is None:
                if not candidate:
                    candidate = part.get_payload(decode=True).decode("utf-8")
                else:
                    raise Exception("two possible candidates!")

        return candidate


if __name__ == "__main__":
    main()

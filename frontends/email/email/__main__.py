from typing import *

import email
import email.message
import email.policy
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import threading
import json
import re
import time
import os

import boto3

import redis


def main():
    email_processor_thread = threading.Thread(target=email_processor, name="email_processor_thread")
    response_processor_thread = threading.Thread(target=response_processor, name="response_processor_thread")

    email_processor_thread.start()
    response_processor_thread.start()

    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            break

    email_processor_thread.join()
    response_processor_thread.join()


def email_processor() -> None:
    client = redis.StrictRedis()

    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName="cecibot-request-bot")  # type: boto3.sqs.Queue

    while True:
        # https://boto3.readthedocs.io/en/latest/reference/services/sqs.html?highlight=get_queue_by_name#SQS.Queue.receive_messages
        messages = queue.receive_messages(WaitTimeSeconds=10)
        if not messages:
            print("no messages received in 20 seconds!")
            continue

        for message in messages:
            body = json.loads(message.body)
            mail = Mail.from_string(json.loads(body["Message"])["content"])

            if mail.subject.startswith(("http://", "https://")):
                url = mail.subject
            else:
                url = None

            print(mail.id_)
            print("From   :", mail.from_)
            print("Subject:", mail.subject)
            print("URL:", url)
            print("--------\n")

            if url:
                n_receivers = client.publish("requests", json.dumps({
                    "url": mail.subject,
                    "medium": "email",

                    "opaque": {
                        "to": mail.from_[0],
                        "in_reply_to": mail.id_,
                    },

                    "identifier": {
                        "headers": mail.headers
                    }
                }))

                """
                if n_receivers != 2:
                    print("The request is received by other than 2 receivers!")
                    print("This might be an indicator that the monitor (or the fetcher) is not working.")
                    print("Exiting...")
                    sys.exit()
                """

            message.delete()


def response_processor() -> None:
    ses = boto3.client("ses")

    client = redis.StrictRedis()
    sub = client.pubsub()

    sub.subscribe("emailResponses")

    # Ignore (the very first) "subscribe" message
    assert sub.get_message(timeout=None)["type"] == "subscribe"

    print("cecibot-email is ready for responses!")

    for response_msg in sub.listen():
        response = json.loads(response_msg["data"])

        if response["kind"] == "file":
            print("IRT", response["opaque"].get("in_reply_to"))

            email_msg = compose_email(
                to=response["opaque"]["to"],
                subject=response["file"]["title"],
                attachment_path=response["file"]["path"],
                in_reply_to=response["opaque"].get("in_reply_to"),
            )

            os.unlink(response["file"]["path"])

            response = ses.send_raw_email(
                Source="bot@cecibot.com",
                Destinations=[response["opaque"]["to"]],
                RawMessage={"Data": email_msg.as_string()},
            )

            if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                print("send_raw_email HTTPStatusCode is not 200! {}".format(response["ResponseMetadata"]["HTTPStatusCode"]))
        elif response["kind"] == "error":
            print("RESPONSE ERROR!!!")
            print(response)

    sub.unsubscribe()
    sub.close()


def compose_email(to: str, *, subject: Optional[str] = None, plaintext_message: Optional[str] = None,
                  attachment_path: Optional[str] = None,
                  in_reply_to: Optional[str] = None, from_: str = "bot@cecibot.com") -> MIMEMultipart:
    # Modified from:
    # https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-raw.html

    assert type(to) is str
    assert type(from_) is str
    assert type(subject) in [type(None), str]
    assert type(in_reply_to) in [type(None), str]
    assert type(plaintext_message) in [type(None), str]
    assert type(attachment_path) in [type(None), str]

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart("mixed")

    msg["From"] = from_
    msg["To"] = to
    if subject is not None:
        msg["Subject"] = subject
    if in_reply_to is not None:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    if plaintext_message is not None:
        # Create a multipart/alternative child container.
        msg_body = MIMEMultipart("alternative")

        # Encode the text and HTML content and set the character encoding. This step is
        # necessary if you're sending a message with characters outside the ASCII range.
        textpart = MIMEText(plaintext_message.encode("utf-8"), "plain", "utf-8")

        # Add the text and HTML parts to the child container.
        msg_body.attach(textpart)

        # Attach the multipart/alternative child container to the multipart/mixed
        # parent container.
        msg.attach(msg_body)

    if attachment_path is not None:
        with open(attachment_path, "rb") as fd:
            # Define the attachment part and encode it using MIMEApplication.
            att = MIMEApplication(fd.read())

        # Add a header to tell the email client to treat this part as an attachment,
        # and to give the attachment a name.
        att.add_header("Content-Disposition", "attachment", filename=os.path.basename(attachment_path))

        # Add the attachment to the parent container.
        msg.attach(att)

    return msg


class Mail:
    def __init__(self):
        self.id_ = None  # type: Optional[str]
        # (e-mail address, name)
        self.from_ = None  # type: Tuple[str, Optional[str]]
        self.subject = None  # type: str
        self.body = None  # type: str
        self.headers = None  # type: Dict[str, str]

    @classmethod
    def from_string(cls, s: str) -> "Mail":
        self = cls()
        msg = email.message_from_string(s, policy=email.policy.default)

        self.id_ = msg.get("Message-ID")
        self.from_ = self._get_from(msg)
        self.subject = self._get_subject(msg)
        self.body = self._get_body(msg)
        self.headers = {k: v for k, v in msg.items()}

        return self

    @staticmethod
    def _get_from(msg: email.message.EmailMessage) -> Tuple[str, Optional[str]]:
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
            return m[3], None
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

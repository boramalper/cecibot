from typing import *

import email
import email.message
import email.policy
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import logging
import re
import textwrap


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

        self.id_ = str(msg.get("Message-ID"))
        self.from_ = self._get_from(msg)
        self.subject = self._get_subject(msg)
        self.body = self._get_body(msg)
        self.headers = {k: v for k, v in msg.items()}

        NoneType = type(None)
        assert isinstance(self.id_, (NoneType, str))
        assert isinstance(self.from_[0], str)
        assert isinstance(self.from_[1], (NoneType, str))
        assert isinstance(self.subject, str)
        assert isinstance(self.body, str)
        assert isinstance(self.headers, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in self.headers.items())

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
        elif m[2]:
            return m[2], None
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

    def __str__(self):
        return textwrap.dedent("""\
            ID     : {}
            From   : {}<{}>
            Subject: {}

            {}
            <<<<<<<<<<<<<<<<<<<<
            <<<<<<<<<<<<<<<<<<<<
            """.format(self.id_, self.from_[1] if self.from_[1] else "", self.from_[0], self.subject, self.body))


def compose(to: str, *, subject: Optional[str] = None, plaintext_message: Optional[str] = None,
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


def send(ses, destination: str, message: MIMEMultipart, source: str = "bot@cecibot.com") -> None:
    response = ses.send_raw_email(
        Source=source,
        Destinations=[destination],
        RawMessage={"Data": message.as_string()},
    )

    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        logging.debug("send_raw_email HTTPStatusCode is not 200! {}".format(response["ResponseMetadata"]["HTTPStatusCode"]))

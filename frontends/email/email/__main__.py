import enum
import threading
import json
import time
import os
import logging
import textwrap
import traceback
import sys

import boto3

import redis

import address
import email2


COOL_DOWN = 30  # cool-down period in seconds
MAX_ATTEMPTS = 20


@enum.unique
class RateLimitingStatus(enum.Enum):
    FREE = enum.auto()
    RATE_LIMITED_NOW = enum.auto()
    RATE_LIMITED_AGAIN = enum.auto()
    BLACKLISTED = enum.auto()


def main() -> int:
    logging.basicConfig(format="%(asctime)s  %(levelname)s\t%(message)s", level=logging.INFO)

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

    return os.EX_OK


def email_processor() -> None:
    client = redis.StrictRedis()

    ses = boto3.client("ses")
    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName="cecibot-request-bot")  # type: boto3.sqs.Queue

    while True:
        # https://boto3.readthedocs.io/en/latest/reference/services/sqs.html?highlight=get_queue_by_name#SQS.Queue.receive_messages
        sqs_messages = queue.receive_messages(WaitTimeSeconds=20)
        if not sqs_messages:
            logging.debug("No SQS messages received in the past 20 seconds!")
            continue

        mails = []
        for sqs_msg in sqs_messages:
            try:
                mail = email2.Mail.from_string(
                    json.loads(
                        json.loads(sqs_msg.body)["Message"]
                    )["content"]
                )
            except:
                traceback.print_exc()
                continue
            finally:
                sqs_msg.delete()

            mails.append(mail)

        for mail in mails:
            rls = rate_limit(client, mail.from_[0])
            if rls == RateLimitingStatus.RATE_LIMITED_NOW:
                email2.send(ses, mail.from_[0], email2.compose(
                    to=mail.from_[0],
                    in_reply_to=mail.id_,
                    subject="cecibot error: rate-limited",
                    plaintext_message=textwrap.dedent("""\
                    Your request
                    
                    \t{}
                    
                    has failed due to rate-limiting. Please try again in {} seconds.
                    
                    ___________
                    cecibot.com
                    """.format(mail.subject, COOL_DOWN))
                ))
            elif rls != RateLimitingStatus.FREE:
                continue

            if not mail.subject.startswith(("http://", "https://")):
                email2.send(ses, mail.from_[0], email2.compose(
                    to=mail.from_[0],
                    in_reply_to=mail.id_,
                    subject="cecibot error: subject is not a URL",
                    plaintext_message=textwrap.dedent("""\
                    Your request
                    
                    \t{}
                    
                    has failed since the request (subject line) seems not to be a URL.
                    
                    Bear in mind that a URL must start with a protocol (i.e. `http://`
                    or `https://`, which are currently the only protocols we support).
                    
                    ___________
                    cecibot.com 
                    """.format(mail.subject))
                ))

            client.lpush("requests", json.dumps({
                "url": mail.subject,
                "medium": "email",

                "opaque": {
                    "to": mail.from_[0],
                    "in_reply_to": mail.id_,
                },

                "identifier_version": 1,
                "identifier": {
                    "headers": mail.headers
                }
            }))


def rate_limit(client: redis.StrictRedis, addr: str) -> RateLimitingStatus:
    counter_name = get_counter_name(addr)

    ttl = client.ttl(counter_name)

    # ttl == -1
    # "The key exists but has no associated expire."
    # Meaning, that the e-mail address/domain is blacklisted.
    if ttl == -1:
        return RateLimitingStatus.BLACKLISTED
    # ttl == -2
    # "The key does not exist."
    # Meaning, that the e-mail address/domain is new.
    elif ttl == -2:
        client.setex(counter_name, COOL_DOWN, 0)
        return RateLimitingStatus.FREE
    # ttl >= 0
    # Meaning, tha the e-mail address/domain is (or rather, should be) cooling down.
    # Keep track of their *attempts* and if it exceeds a certain number, blacklist them.
    elif ttl >= 0:
        n_attempts = client.incr(counter_name)

        if n_attempts >= MAX_ATTEMPTS:
            client.set(counter_name, 0)
            return RateLimitingStatus.BLACKLISTED
        elif n_attempts == 1:
            return RateLimitingStatus.RATE_LIMITED_NOW
        else:
            return RateLimitingStatus.RATE_LIMITED_AGAIN


def get_counter_name(addr: str) -> str:
    local, domain = address.separate(addr)

    rdomain = address.whitedict.get(domain)
    if rdomain is None:
        return "email.rate_limiting.counter.nolocal.({})".format(address.reversed_domain(domain))
    else:
        return "email.rate_limiting.counter.complete.({}).({})".format(rdomain, address.normalise_local(local))


def response_processor() -> None:
    ses = boto3.client("ses")

    client = redis.StrictRedis()

    logging.info("cecibot-email is ready for responses!")

    while True:
        response = json.loads(client.brpop("email_responses")[1])

        if response["kind"] == "error":
            email2.send(ses, response["opaque"]["to"], email2.compose(
                to=response["opaque"]["to"],
                in_reply_to=response["opaque"].get("in_reply_to"),
                subject="cecibot error: {}".format(response["error"]["message"]),
                plaintext_message=textwrap.dedent("""\
                Your request
    
                \t{}
    
                has been unsuccessful due to following error:
                
                \t{}
                  
                ___________
                cecibot.com
                """.format(response["url"], response["error"]["message"]))
            ))
            continue

        # If not error, send the file (kind == file)
        email2.send(ses, response["opaque"]["to"], email2.compose(
            to=response["opaque"]["to"],
            subject=response["file"]["title"],
            attachment_path=response["file"]["path"],
            in_reply_to=response["opaque"].get("in_reply_to"),
        ))
        os.unlink(response["file"]["path"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except:
        print("UNCAUGHT EXCEPTION!")
        traceback.print_exc()
        sys.exit(os.EX_SOFTWARE)

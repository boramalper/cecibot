from typing import *

# Do NOT add ANY domains of the following e-mail service providers (as they seem fishy...):
#
# - Mail.com
# - Runbox
__whitelist = [
    "aol.com",

    "hotmail.com",
    "outlook.com",

    "gmail.com",
    "googlemail.com",

    "tutanota.com",
    "tutanota.de",
    "tutamail.com",
    "tuta.io",
    "keemail.me",

    "protonmail.com",
    "protonmail.ch",

    "icloud.com",
    "me.com",
    "mac.com",

    "rediffmail.com",

    "yahoo.com",

    "yandex.com",
    "yandex.ru",

    "mail.ru",

    "zoho.com",
    "zoho.eu",

    "hushmail.com",
    "hushmail.me",
    "hush.com",
    "hush.ai",
    "mac.hush.com",

    "fastmail.com",
    "fastmail.cn",
    "fastmail.co.uk",
    "fastmail.com.au",
    "fastmail.de",
    "fastmail.es",
    "fastmail.fm",
    "fastmail.fr",
    "fastmail.im",
    "fastmail.in",
    "fastmail.jp",
    "fastmail.mx",
    "fastmail.net",
    "fastmail.nl",
    "fastmail.org",
    "fastmail.se",
    "fastmail.to",
    "fastmail.tw",
    "fastmail.uk",
    "fastmail.us",
    "123mail.org",
    "airpost.net",
    "eml.cc",
    "fmail.co.uk",
    "fmgirl.com",
    "fmguy.com",
    "mailbolt.com",
    "mailcan.com",
    "mailhaven.com",
    "mailmight.com",
    "ml1.net",
    "mm.st",
    "myfastmail.com",
    "proinbox.com",
    "promessage.com",
    "rushpost.com",
    "sent.as",
    "sent.at",
    "sent.com",
    "speedymail.org",
    "warpmail.net",
    "xsmail.com",
    "150mail.com",
    "150ml.com",
    "16mail.com",
    "2-mail.com",
    "4email.net",
    "50mail.com",
    "allmail.net",
    "bestmail.us",
    "cluemail.com",
    "elitemail.org",
    "emailcorner.net",
    "emailengine.net",
    "emailengine.org",
    "emailgroups.net",
    "emailplus.org",
    "emailuser.net",
    "f-m.fm",
    "fast-email.com",
    "fast-mail.org",
    "fastem.com",
    "fastemail.us",
    "fastemailer.com",
    "fastest.cc",
    "fastimap.com",
    "fastmailbox.net",
    "fastmessaging.com",
    "fea.st",
    "fmailbox.com",
    "ftml.net",
    "h-mail.us",
    "hailmail.net",
    "imap-mail.com",
    "imap.cc",
    "imapmail.org",
    "inoutbox.com",
    "internet-e-mail.com",
    "internet-mail.org",
    "internetemails.net",
    "internetmailing.net",
    "jetemail.net",
    "justemail.net",
    "letterboxes.org",
    "mail-central.com",
    "mail-page.com",
    "mailandftp.com",
    "mailas.com",
    "mailc.net",
    "mailforce.net",
    "mailftp.com",
    "mailingaddress.org",
    "mailite.com",
    "mailnew.com",
    "mailsent.net",
    "mailservice.ms",
    "mailup.net",
    "mailworks.org",
    "mymacmail.com",
    "nospammail.net",
    "ownmail.net",
    "petml.com",
    "postinbox.com",
    "postpro.net",
    "realemail.net",
    "reallyfast.biz",
    "reallyfast.info",
    "speedpost.net",
    "ssl-mail.com",
    "swift-mail.com",
    "the-fastest.net",
    "the-quickest.com",
    "theinternetemail.com",
    "veryfast.biz",
    "veryspeedy.net",
    "yepmail.net",
    "your-mail.com",
]


def is_valid(local: str, domain: str) -> bool:
    return local[0].isalnum() and all(map(lambda ch: ch.isalnum() or ch in ["+", "-", ".", "_"], local))


def separate(addr: str) -> Tuple[str, str]:
    try:
        local, domain = addr.split("@")
    except ValueError:
        raise

    return local, domain


def normalise_local(local: str) -> str:
    """
    Given an e-mail address (as a tuple of local & domain) returns the *normalised* version of it (again as a tuple).

    For instance:

      - GMail ignores periods (`.`) in the local so all of them will be removed.
      - Many e-mail providers use the part after plus (`+`) to allow users tag incoming e-mails automatically, so the
        part after the plus will be ignored.
      - and so on...

    :param local:
    :return:
    """
    # Strip the label
    plus_i = local.find("+")
    if plus_i != -1:
        local = local[:plus_i]

    # Remove dots
    return local.replace(".", "")


def reversed_domain(domain):
    return ".".join(reversed(domain.split(".")))


whitedict = {d: reversed_domain(d) for d in __whitelist}

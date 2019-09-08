#! env python3
import sys
import os
import logging
import requests
from dateparser import parse
import configparser

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config'))

BOT_TOKEN = config["default"]["BOT_TOKEN"]
BOT_CHAT = config["default"]["BOT_CHAT"]

settings = {"PREFER_DATES_FROM": 'future'}

def getMessageAndTime(args):
    if args[1] == '/t':
        whenstr, argi = "", 2
        while args[argi] != "/m":
            whenstr = whenstr + " " + args[argi]
            argi = argi + 1
        when = parse(whenstr, settings=settings)
        message = " ".join(args[argi + 1:])
        return (when, message)
    message = " ".join(args[1:])
    return (None, message)

def main(args):
    """TODO: Docstring for main.
    :returns: TODO

    """
    when, message = getMessageAndTime(args)
    print(when, message)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={BOT_CHAT}&text={message}"
    print(url)
    if not when:
        r = requests.post(url)
        print(r.text)

if __name__ == "__main__":
    main(sys.argv)

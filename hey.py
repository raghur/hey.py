#! env python3
import sys
import os
import logging
import requests
from dateparser import parse
from dateparser.search import search_dates
import configparser

config = configparser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config'))

BOT_TOKEN = config["default"]["BOT_TOKEN"]
BOT_CHAT = config["default"]["BOT_CHAT"]

settings = {"PREFER_DATES_FROM": 'future'}
def getMessageAndTime(args):
    if args[1] == '/t':
        when = parse(args[2], settings=settings)
        message = " ".join(args[4:])
        return (when, message)
    message = " ".join(args[1:])
    dates =search_dates(message, settings=settings)
    if len(dates) > 0:
        when = dates[0][1]
        message = message.replace(dates[0][0], "")
        return (when, message)
def main(args):
    """TODO: Docstring for main.
    :returns: TODO

    """
    when, message = getMessageAndTime(args)
    print(when, message)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={BOT_CHAT}&text={message}"
    print(url)
    # r = requests.post(url)
    # print(r.text)

if __name__ == "__main__":
    main(sys.argv)

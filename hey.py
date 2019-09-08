#!/usr/bin/env python3
import sys
import os
import logging
import requests
from dateparser import parse
import configparser
import subprocess

SETTINGS = {"PREFER_DATES_FROM": 'future'}
FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.WARNING)

def readConfig():
    config = configparser.ConfigParser()
    config_path1 = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config')
    config_path2 = "/etc/hey.conf"
    config_path3 = os.path.expanduser("~/.config/hey.conf")
    config.read([config_path1, config_path2, config_path3])
    return config


def getMessageAndTime(args):
    if args[1] == '/t':
        whenstr, argi = "", 2
        while args[argi] != "/m":
            whenstr = whenstr + " " + args[argi]
            argi = argi + 1
        when = parse(whenstr, settings=SETTINGS)
        message = " ".join(args[argi + 1:])
        return (when, message)
    message = " ".join(args[1:])
    return (None, message)

def main(args):
    """TODO: Docstring for main.
    :returns: TODO

    """
    config = readConfig()
    BOT_TOKEN = config["default"]["BOT_TOKEN"]
    BOT_CHAT = config["default"]["BOT_CHAT"]
    when, message = getMessageAndTime(args)
    logging.debug(when, message)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={BOT_CHAT}&text={message}"
    logging.debug(url)
    if not when:
        r = requests.post(url)
        logging.debug(r.text)
        return 0 # fix this based on http status
    else:
        timestr = when.strftime("%I:%M %p %Y-%m-%d")
        status = subprocess.run(["at", timestr],
                                input=f"{os.path.abspath(__file__)} {message}",
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                encoding="utf8")
        if status.returncode == 0:
            print(f"reminder '{message}' set for {timestr}")
            return 0
        else:
            print("Setting reminder with at failed. Here's the output of at")
            print(status.stdout)
            print(status.stderr)
            return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))

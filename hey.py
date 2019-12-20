#!/usr/bin/env python3
import sys
import os
import logging
import configparser
import subprocess
from datetime import datetime
from urllib.parse import quote_plus, unquote_plus
import pytz

from dateparser import parse
import argparse
import requests

LEVEL = logging.DEBUG
SETTINGS = {'PREFER_DATES_FROM': 'future'}
FORMAT = ("%(asctime)s %(levelname)s (%(threadName)s) "
          "[%(name)s] %(message)s")
logging.basicConfig(format=FORMAT, level=LEVEL)


def readConfig():
    config = configparser.ConfigParser()
    config_path1 = os.path.join(os.path.abspath(
        os.path.dirname(__file__)), 'config')
    config_path2 = "/etc/hey.conf"
    config_path3 = os.path.expanduser("~/.config/hey.conf")
    config.read([config_path1, config_path2, config_path3])
    return config


def isInThePast(when):
    return (getLocalizedDate(when) - getLocalizedDate()).total_seconds() < 0

def parseTime(whenstr):
    logging.debug(whenstr)
    when = parse(whenstr.strip(), settings=SETTINGS)
    if not when:
        raise ValueError(
            "Could not parse time expression '{}'".format(whenstr))
    if isInThePast(when):
        # see https://github.com/scrapinghub/dateparser/issues/563
        when = parse("in " + whenstr,
                     settings=SETTINGS)
        if not when:
            raise ValueError(
                "Could not parse time expression 'in {}'".format(whenstr))
        if isInThePast(when):
            raise ValueError(
                "Parsing '{0}' and 'in {0}' did not yield a future date"
                .format(whenstr))
    return when


def printTimeExpressionHelp():
    print("""Time expression examples:
    in 10 minutes
    in 1 month
    next week
    friday 10 AM
    wed 10 AM
    10 AM Tues
Refer to https://dateparser.readthedocs.io/en/latest/ for documentation on date
expressions""")


def parseArgs(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", nargs="+", type=str, dest="time",
                            help="word", metavar="WORD")
    parser.add_argument("-m", nargs="+", type=str, dest="msg")
    parser.add_argument("-r", dest="repeat", choices=["qh", "hh", "h", "d",
                                                        "wk", "bw", "mly", "qly",
                                                        "hly", "yly"],
                        help="""Non functional
qh   - 15 mins
hh   - 30 mins
h    - hourly
d    - daily
wk   - weekly
bw   - bi weekly (2 weeks)
mly  - monthly
qly  - quarterly (3 months)
hly  - half yearly
yly  - yearly
""")
    parser.add_argument("-c", type=int, default=10, metavar="COUNT",
                        help="Repeat count (Default: %(default)s)")
    parsedArgs = parser.parse_args(args)
    if parsedArgs.time:
        when = parseTime(" ".join(parsedArgs.time))
        parsedArgs.time = when
    parsedArgs.msg = " ".join(parsedArgs.msg)
    return parsedArgs


def getLocalizedDate(date=None):
    if date is None:
        date = datetime.now()
    if "TIMEZONE" not in SETTINGS:
        return date
    return date.astimezone(pytz.timezone(SETTINGS["TIMEZONE"]))


def main(args):
    """TODO: Docstring for main.
    :returns: TODO

    """
    parsedArgs = parseArgs(args)
    logging.debug(args)
    config = readConfig()
    BOT_TOKEN = config["default"]["BOT_TOKEN"]
    BOT_CHAT = config["default"]["BOT_CHAT"]
    if "TIMEZONE" in config["default"]:
        SETTINGS["TIMEZONE"] = config["default"]["TIMEZONE"]
        SETTINGS["TO_TIMEZONE"] = "UTC"
    try:
        when, message = (parsedArgs.time, parsedArgs.msg)
        logging.debug("%s, %s", when, message)
    except ValueError as ve:
        print(str(ve))
        printTimeExpressionHelp()
        return 1

    # sys.exit(1)
    if not when:
        unquoted = unquote_plus(message)
        if 'Created:' in unquoted:
            timestr = getLocalizedDate().strftime("%I:%M %p")
            # add current time to message
            message = quote_plus("{}: {}".format(timestr, unquoted))
        url = ("https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}"
               .format(BOT_TOKEN, BOT_CHAT, message))
        logging.debug(url)
        r = requests.post(url)
        logging.debug(r.json())
        if r.json()["ok"]:
            return 0
        logging.error("Error sending telegram req - %s", r.json())
        return 1
    else:
        timestr = when.strftime("%I:%M %p %Y-%m-%d")
        nowstr = getLocalizedDate().strftime("%a %I:%M %p %d %b %y")
        qparam = quote_plus("{} \r\nCreated: {}".format(message, nowstr))
        input = bytes("{} -m {}".format(
            os.path.abspath(__file__), qparam), "utf8")
        logging.debug("Setting at call %s, %s", timestr, input)
        status = subprocess.run(["at", timestr],
                                input=input,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if status.returncode == 0:
            timestr = getLocalizedDate(when).strftime("%I:%M %p %Y-%m-%d")
            print("reminder '{}' set for {}".format(message, timestr))
            return 0
        else:
            print("Setting reminder with at failed. Here's the output of at")
            print(status.stdout)
            print(status.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

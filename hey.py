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

LEVEL = logging.INFO
SETTINGS = {'PREFER_DATES_FROM': 'future'}
FORMAT = ("%(asctime)s %(levelname)s (%(threadName)s) "
          "[%(name)s] %(message)s")
logging.basicConfig(format=FORMAT, level=LEVEL)

REPEAT_LOOKUP = {
    "qh": "15m",
    "hh": "30m",
    "h": "in 1h",
    "d": "in 1 day",
    "wk": "in 1 week",
    "bw": "in 2 weeks",
    "mly": "in 1 month",
    "hly": "in 6 months",
    "yly": "in 1 year",
}
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
    parser.add_argument("-r", dest="repeatExpr", choices=REPEAT_LOOKUP.keys(),
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
    parser.add_argument("-c", dest="count", type=int, default=10, metavar="COUNT",
                        help="Repeat count (Default: %(default)s)")
    parser.add_argument("-o", dest="initial_repeat", type=int,
                        help=argparse.SUPPRESS)
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
    logging.debug(parsedArgs)
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
        # only message content - just send
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
        # has a time component
        timestr = when.strftime("%I:%M %p %Y-%m-%d")
        nowstr = getLocalizedDate().strftime("%a %I:%M %p %d %b %y")
        msg = "{} \r\nCreated: {}".format(message, nowstr)
        if parsedArgs.count and parsedArgs.count == 1:
            msg = "{} \r\n Original repeat was {} times".format(msg,
                                                      parsedArgs.origCount)

        qparam = quote_plus(msg)
        atcmd = "{} -m {}".format(os.path.abspath(__file__), qparam)
        if parsedArgs.count and parsedArgs.count > 0:
            msg = message
            origCount = parsedArgs.count
            if parsedArgs.initial_repeat:
                origCount = parsedArgs.initial_repeat
            whenExpr = REPEAT_LOOKUP[parsedArgs.repeatExpr]
            repeatCmd = "{} -t {} -m {} -c {} -o {}".format(os.path.abspath(__file__), whenExpr, msg, parsedArgs.count - 1,
                                            origCount)
            logging.debug("Repeat cmd: %s", repeatCmd)
            atcmd = "{} \r\n{}".format(atcmd, repeatCmd)

        input = bytes(atcmd, "utf8")
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

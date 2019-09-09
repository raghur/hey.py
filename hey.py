#!/usr/bin/env python3
import sys
import os
import logging
import configparser
import subprocess
from datetime import datetime
from urllib.parse import quote_plus, unquote_plus

from dateparser import parse
import requests

LEVEL = logging.WARNING
SETTINGS = {'PREFER_DATES_FROM': 'future'}
FORMAT = ("%(asctime)s %(levelname)s (%(threadName)s) "
           "[%(name)s] %(message)s")
logging.basicConfig(format=FORMAT, level=LEVEL)

def readConfig():
    config = configparser.ConfigParser()
    config_path1 = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config')
    config_path2 = "/etc/hey.conf"
    config_path3 = os.path.expanduser("~/.config/hey.conf")
    config.read([config_path1, config_path2, config_path3])
    return config


def getMessageAndTime(args):
    if args[1] == '/t' or args[1] == "-t":
        whenstr, argi = "", 2
        while args[argi] != "/m" and args[argi] != '-m':
            whenstr = whenstr + " " + args[argi]
            argi = argi + 1
        whenstr = whenstr.strip()
        logging.debug(whenstr)
        when = parse(whenstr, settings={'PREFER_DATES_FROM': 'future'})
        if not when:
            raise ValueError(f"Could not parse time expression '{whenstr}'") 
        if (when - datetime.now()).total_seconds() < 0:
            # see https://github.com/scrapinghub/dateparser/issues/563
            when = parse("in " + whenstr, settings={'PREFER_DATES_FROM': 'future'})
            if not when:
                raise ValueError(f"Could not parse time expression 'in {whenstr}'") 
            if (when - datetime.now()).total_seconds() < 0:
                raise ValueError(f"Parsing '{whenstr}' and 'in {whenstr}' did not yield a future date") 
        message = " ".join(args[argi + 1:])
        return (when, message)
    message = " ".join(args[1:])
    return (None, message)

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

def printUsage(progName):
    print(f"""Summary: quick and simple cli reminder tool
Usage: {progName} [-t timestring] [[-m] message]

Examples:
{progName} -t 10 mins -m everything here is strung together
    Quotes are only required if your message includes quotes. If not, you can
    just string your message together.

{progName} without args we will send the message right away
    Without any options, the arg list is considered the message and sent 
    immediately.""")
    print()
    printTimeExpressionHelp()
    pass

def main(args):
    """TODO: Docstring for main.
    :returns: TODO

    """
    if len(args) == 1:
        printUsage(args[0])
        return 1
    config = readConfig()
    BOT_TOKEN = config["default"]["BOT_TOKEN"]
    BOT_CHAT = config["default"]["BOT_CHAT"]
    try:
        when, message = getMessageAndTime(args)
        logging.debug("%s, %s", when, message)
    except ValueError as ve:
        print(str(ve))
        printTimeExpressionHelp()
        return 1

    if not when:
        unquoted = unquote_plus(message)
        if 'Created:' in unquoted:
            timestr = datetime.now().strftime("%I:%M %p")
            # add current time to message
            message = quote_plus(f"{timestr}: {unquoted}")
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={BOT_CHAT}&text={message}"
        logging.debug(url)
        r = requests.post(url)
        logging.debug(r.text)
        return 0 # fix this based on http status
    else:
        timestr = when.strftime("%I:%M %p %Y-%m-%d")
        nowstr = datetime.now().strftime("%a %I:%M %p %d %b %y")
        qparam = quote_plus(f"{message} \r\nCreated: {nowstr}")
        status = subprocess.run(["at", timestr],
                                input=f"{os.path.abspath(__file__)} {qparam}",
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

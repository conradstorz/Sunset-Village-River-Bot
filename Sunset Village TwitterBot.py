#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This is a twitterBot that will periodically tweet the projected river level at Bushman's Lake based on the 
NWS website data for the river level both upstream and downstream then calculating the slope of the river
to get the calculated level at our property. 
"""

import time
from datetime import datetime, timezone
from datetime import timedelta
from dateutil import parser

from loguru import logger
logger.remove()  # stop any default logger
LOGGING_LEVEL = "INFO"

from NWS_River_Data_scrape import calculated_Bushmans_river_level as get_level
from pprint import saferepr
from pprint import pprint

from pupdb.core import PupDB

PupDB_FILENAME = "SVTB-DB.json_db"
PupDB_MRTkey = "MostRecentTweet"
PupDB_MRLkey = "MostRecentRiverLevel"
PupDB_ACTIONkey = "CurrentFloodingActionLevel"

ACTION_LABELS = ["First-action", "Minor-flood", "Moderate-flood", "Major-flood"]
ACTION_LEVELS = [21, 23, 30, 38]
ACTION_DICT = dict(zip(ACTION_LEVELS, ACTION_LABELS))

""" flooding action levels for McAlpine dam upper guage in louisville
    "first-action": 21,
    "minor-flood": 23,
    "moderate-flood": 30,
    "major-flood": 38,
"""

from twython import Twython, TwythonError
from TwitterCredentials import APP_KEY
from TwitterCredentials import APP_SECRET
from TwitterCredentials import OAUTH_TOKEN
from TwitterCredentials import OAUTH_TOKEN_SECRET

TWITTER_CREDENTIALS = (APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
MAXIMUM_TWEETS_PER_HOUR = 0.2
MINIMUM_TIME_BETWEEN_TWEETS = 3600 / MAXIMUM_TWEETS_PER_HOUR  # in seconds

from os import sys, path
RUNTIME_NAME = path.basename(__file__)


@logger.catch
def UpdatePrediction(twtr, tm, db):
    """ Returns the time to wait until next tweet and Tweets if enough time has passed
    twtr = twython object for accessing Twitter
    tm = datetime obj representing current time
    db = PupDB obj for persistant storage on local machine
    
    """
    MOST_RECENT_TWEET = db.get(PupDB_MRTkey)  # recover string repr of datetime obj
    prevTweet = parser.parse(MOST_RECENT_TWEET)  # convert back to datetime
    # check tm against minimum tweet time
    logger.info("Time now: " + str(tm))
    logger.info("Previous Tweet time: " + str(prevTweet))
    elapsed = tm - prevTweet  # returns a timedelta object
    logger.info("Time since last Tweet: " + str(elapsed))
    logger.info("Total number of seconds elapsed: " + str(elapsed.total_seconds()))
    if elapsed.total_seconds() >= MINIMUM_TIME_BETWEEN_TWEETS:
        logger.info("Tweeting...")
        waitTime = 0
        x = get_level()  # retrieve river level readings
        sp = saferepr(x)  # use pprint to serialize a version of the result
        db.set(PupDB_MRTkey, str(tm))
        twtr.update_status(status=sp)
        logger.info("Tweet sent.")
        logger.debug("Tweet string = " + str(sp))
        for item in x:
            logger.info(item)
        logger.info("Length of string = ", str(len(saferepr(x))))
    else:
        logger.info("Too soon to tweet.")
        waitTime = MINIMUM_TIME_BETWEEN_TWEETS - elapsed.seconds
        logger.info("Recommend waiting " + str(waitTime) + " seconds.")
    return waitTime


@logger.catch
def Main(credentials):
    defineLoggers()
    # unpack the credentials before submitting to Twython
    a, b, c, d = credentials
    # establish the twitter access object
    twitter = Twython(a, b, c, d)

    # activate PupDB file for persistent storage
    TimeNow = datetime.now()
    storage_db = PupDB(PupDB_FILENAME)
    MOST_RECENT_TWEET = storage_db.get(PupDB_MRTkey)
    if MOST_RECENT_TWEET == None:  # Pre-load empty database
        storage_db.set(PupDB_MRTkey, str(TimeNow))

    while True:
        TimeNow = datetime.now()
        wait = UpdatePrediction(twitter, TimeNow, storage_db)
        time.sleep(wait / 5)  # delay until next check
    return


@logger.catch
def defineLoggers():
    logger.add(
        sys.stderr,
        colorize=True,
        format="<green>{time}</green> {level} <red>{message}</red>",
        level=LOGGING_LEVEL,
    )
    logger.add(  # create a new log file for each run of the program
        "./LOGS/" + RUNTIME_NAME + "_{time}.log",
        retention="10 days",
        compression="zip",
        level="DEBUG",  # always send debug output to file
    )
    return


if __name__ == "__main__":
    Main(TWITTER_CREDENTIALS)

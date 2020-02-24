#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This is a twitterBot that will periodically tweet the projected river level at Bushman's Lake
based on the NWS website data for the river level both upstream and downstream then calculating 
the slope of the river to get the calculated level at our property. 
"""

import time
from datetime import datetime, timezone
from datetime import timedelta
from dateutil import parser

from NWS_River_Data_scrape import calculated_Bushmans_river_level as get_level
from NWS_River_Data_scrape_NEW import processRiverData as get_level_data
from NWS_River_Data_scrape_NEW import RIVER_MONITORING_POINTS
from NWS_River_Data_scrape_NEW import MCALPINE_DAM_NAME as DNRIVERDAM
from NWS_River_Data_scrape_NEW import MARKLAND_DAM_NAME as UPRIVERDAM
from pprint import saferepr
from pprint import pprint
from pupdb.core import PupDB
# detect various add-on Rpi hats
try:
    SenseHatLoaded = True
    from sense_hat import SenseHat
    sense = SenseHat()
except ImportError as e:
    print('Failed to detect "SenseHat" module.')
    SenseHatLoaded = False
print(f'Sense Hat loaded: {SenseHatLoaded}')

PupDB_FILENAME = "SVTB-DB.json_db"
PupDB_MRTkey = "MostRecentTweet"
PupDB_MRLkey = "MostRecentRiverLevel"
PupDB_ACTIONkey = "CurrentFloodingActionLevel"

ACTION_LABELS = [
    "No Flooding",
    "First-action",
    "Minor-flood",
    "Moderate-flood",
    "Major-flood",
]
MINIMUM_CONCERN_LEVEL = 30
TWEET_FREQUENCY = [18000, 9000, 8000, 7000, 6000, 5000, 4000, 3600]  # delay time in seconds
# Time between tweets decreases as flooding increases
# MINIMUM_TIME_BETWEEN_TWEETS = TWEET_FREQUENCY[0]
# ACTION_LEVELS = [21, 23, 30, 38]
# ACTION_DICT = dict(zip(ACTION_LEVELS, ACTION_LABELS))
LOCATION_OF_INTEREST = 584  # river mile marker @ Bushman's Lake
OBSERVATION_TAGS = ["Latest", "Highest"]

from twython import Twython, TwythonError
from TwitterCredentials import APP_KEY
from TwitterCredentials import APP_SECRET
from TwitterCredentials import OAUTH_TOKEN
from TwitterCredentials import OAUTH_TOKEN_SECRET

TWITTER_CREDENTIALS = (APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)


from os import sys, path

RUNTIME_NAME = path.basename(__file__)

from loguru import logger

logger.remove()  # stop any default logger
LOGGING_LEVEL = "INFO"


@logger.catch
def test_tweet(db):
    data = get_level_data()
    # data contains ALL "imortant" levels
    # logger.debug(str(data))
    # TODO create function to extract only 6 most relevent current,highest,eventual levels
    return build_tweet(data, db)


@logger.catch
def send_tweet(db, tm, tweet, twttr):
    """Accept a datetime object, a tweet string and a Twython object. Place tweet and updtae filesystem storage to reflect activities.
    """
    # place tweet time into longterm storage
    db.set(PupDB_MRTkey, str(tm))
    # place tweet into longterm storage. Keep ALL tweets keyed on timestamp
    tweetKey = f'Tweet@{tm}'
    db.set(tweetKey, tweet)
    try:
        twttr.update_status(status=tweet)
    except TwythonError as e:
        logger.error(str(e))
        logger.info("Tweet not sent.")
    else:
        logger.info("Tweet sent.")
    finally:
        logger.debug("Tweet string = " + str(tweet))
        logger.info("Length of string = " + str(len(tweet)))
    return True


@logger.catch
def sanitize(itm):
    """ Observations from NOAA have a format discrepacy between 'Latest' entries
    and all other forms of entry. This function looks for those entries and
    'Standardizes' them.
    """
    sani = itm
    if itm[0] == "Latest":
        logger.debug(itm)
        tail = itm[3:]
        sani = [itm[0], "Observation:"]
        for i in tail:
            sani.append(i)
        logger.debug(sani)
    return sani


@logger.catch
def extract_data(map_data, lbl_str):
    """ take the 'map' data dict and extract entries matching supplied label.
    We know the 'map' contains entries of observations and forecasts. Each entry
    has the name of the dam as the last item three from the end of the line.
    """
    # scan dictionary for specified observations
    observations = {}
    for line in map_data.keys():
        if map_data[line][0] == lbl_str:
            key = f"{map_data[line][-3]}{map_data[line][-1]}"
            observations[key] = sanitize(map_data[line])
    return observations


@logger.catch
def extract_forecast(obsv_data):
    """ take the 'obsv' data dict and extract entries matching forecast predictions.
    We know the 'obsv' contains entries of observations and forecasts. Each entry
    has the name of the dam as the last item three from the end of the line.
    We want one prediction for each dam.
    """
    # scan dictionary for specified observations
    observations = {}
    for line in obsv_data.keys():
        damname = obsv_data[line][-3]
        if obsv_data[line][1] == "Forecast:":
            if damname not in observations.keys():
                observations[damname] = obsv_data[line]
                logger.debug("Forecast line:")
                logger.debug(observations[damname])
    return observations


@logger.catch
def extract_latest(obsv_data):
    """ take the 'obsv' data dict and extract entries matching latest predictions.
    We know the 'obsv' contains entries of observations and forecasts. Each entry
    has the name of the dam as the last item three from the end of the line.
    We want one observation of the latest level for each dam.
    """
    # scan dictionary for specified observations
    observations = {}
    logger.debug("Scanning for latest observations:")
    for line in obsv_data.keys():
        logger.debug(obsv_data[line])
        damname = obsv_data[line][-3]
        if obsv_data[line][0] == "Latest":
            if damname not in observations.keys():
                observations[damname] = obsv_data[line]
                logger.debug("Latest line:")
                logger.debug(observations[damname])
    return observations


@logger.catch
def assemble_text(dict_data, db):
    for key in dict_data.keys():
        logger.debug("assemble tweet input line:")
        logger.debug(f"Entry[{key}]:{str(dict_data[key])}")
        dt = dict_data[key][-1]
        level_obsrvd = float(dict_data[key][2])
        milemrkr = float(dict_data[key][-4])
        elevate = float(dict_data[key][-2])
        if dict_data[key][-3] == UPRIVERDAM:
            upriver_name = f"{key}{dt}"
            upriver_level = level_obsrvd
            upriver_milemrkr = milemrkr
            upriver_elevation = elevate
        if dict_data[key][-3] == DNRIVERDAM:
            dnriver_name = f"{key}{dt}"
            dnriver_level = level_obsrvd
            dnriver_milemrkr = milemrkr
            dnriver_elevation = elevate
    # calculate bushmans level based on latest observation
    slope = upriver_level - dnriver_level
    # correct for difference in elevation of guages
    elev_diff = upriver_elevation - dnriver_elevation
    slope = slope - elev_diff
    # determine pool size
    pool_length = dnriver_milemrkr - upriver_milemrkr
    # calculate an average slope for the pool
    per_mile_slope = slope / pool_length
    # calculate projected level
    projection = (
        dnriver_milemrkr - LOCATION_OF_INTEREST
    ) * per_mile_slope + dnriver_level
    # build text of tweet
    t1 = f"Latest Observation: {upriver_name} {upriver_level}ft"
    t2 = f" {dnriver_name} {dnriver_level}ft"
    t3 = f" Calculated Level at Bushmans: {projection:.2f}ft"
    tweet = t1 + t2 + t3 + " ::: Data source: http://portky.com/river.php"
    logger.info(tweet)
    logger.info(f"Length of Tweet {len(tweet)} characters.")
    # place this river level projection into longterm storage database
    db.set(PupDB_MRLkey, projection)
    return tweet


@logger.catch
def build_tweet(rivr_conditions_dict, db):
    """takes a dictionary of river condition observations from 2 dams and builds data into a tweet.
    """
    tweet = " "
    # TODO put these data gathering functions in seperate functions and return named tuples of results
    # TODO (damname,observationtype,timestamp,level)
    # TODO organize data as: currentobservation,highestforecast,eventualforecast)
    """
    from collections import namedtuple

    Event = namedtuple('DamData', ['DamName', 'ObsvType', 'TimeStamp', 'Level'])
    Event.__new__.__defaults__ = (None, None, None, None)
    E1 = Event()
    E2 = Event('McAlpine', 'Forecast', TimeNow(), '12.98')
    assert E2.DamName == 'McAlpine'
    assert E1.DamName == None
    """
    obsv_dict = {}
    for lbl in OBSERVATION_TAGS:
        obsv_dict.update(extract_data(rivr_conditions_dict, lbl))
    # extract 1 latest observation for each dam
    latest_dict = extract_latest(obsv_dict)
    # TODO extract 1 forecast level for each dam
    # forecast_dict = extract_forecast(obsv_dict)
    tweet = assemble_text(latest_dict, db)
    return tweet


@logger.catch
def UpdatePrediction(twtr, tm, db):
    """ Returns the time to wait until next tweet and Tweets if enough time has passed
    twtr = twython object for accessing Twitter
    tm = datetime obj representing current time
    db = PupDB obj for persistant storage on local machine
    """
    MOST_RECENT_TWEET_TIME = db.get(PupDB_MRTkey)  # recover string repr of datetime obj
    prevTweet = parser.parse(MOST_RECENT_TWEET_TIME)  # convert back to datetime
    MOST_RECENT_LEVEL = db.get(PupDB_MRLkey)  # recover recent level
    # TODO figure out how to initialize database with a default reading
    # TODO for now i'm inserting it manually
    priority = int(MOST_RECENT_LEVEL - MINIMUM_CONCERN_LEVEL)
    if priority < 0: 
        priority = 0
    if priority > len(TWEET_FREQUENCY):
        priority = len(TWEET_FREQUENCY) - 1
    logger.info("Priority: " + str(priority))
    MINIMUM_TIME_BETWEEN_TWEETS = TWEET_FREQUENCY[priority]
    logger.info("Time between Tweets: " + str(MINIMUM_TIME_BETWEEN_TWEETS))
    # check tm against minimum tweet time
    logger.info("Time now: " + str(tm))
    logger.info("Previous Tweet time: " + str(prevTweet))
    elapsed = tm - prevTweet  # returns a timedelta object
    logger.info("Time since last Tweet: " + str(elapsed))
    logger.info("Total number of seconds elapsed: " + str(elapsed.total_seconds()))
    if elapsed.total_seconds() >= MINIMUM_TIME_BETWEEN_TWEETS:
        logger.info("Tweeting...")
        waitTime = 0
        data = get_level_data()
        sp = build_tweet(data, db)
        send_tweet(db, tm, sp, twtr)
    else:
        logger.info("Too soon to tweet.")
        waitTime = MINIMUM_TIME_BETWEEN_TWEETS - elapsed.seconds
        logger.info("Recommend waiting " + str(waitTime) + " seconds.")
    return (waitTime, MOST_RECENT_LEVEL)


@logger.catch
def DisplayLevel(level):
    if SenseHatLoaded:
        sense.show_message(f'Latest level {level:.2f}ft')


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
    MOST_RECENT_LEVEL = storage_db.get(PupDB_MRLkey)
    if MOST_RECENT_TWEET == None:  # Pre-load empty database
        MOST_RECENT_TWEET = str(TimeNow)
        MOST_RECENT_LEVEL = MINIMUM_CONCERN_LEVEL
        storage_db.set(PupDB_MRTkey, MOST_RECENT_TWEET)
        storage_db.set(PupDB_MRLkey, MOST_RECENT_LEVEL)      
    while True:
        TimeNow = datetime.now()
        wait, MOST_RECENT_LEVEL = UpdatePrediction(twitter, TimeNow, storage_db)
        DisplayLevel(MOST_RECENT_LEVEL)
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

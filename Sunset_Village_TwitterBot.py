#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This is a twitterBot that will periodically tweet the projected river level at Bushman's Lake
based on the NWS website data for the river level both upstream and downstream then calculating 
the slope of the river to get the calculated level at our property. 
"""
from pprint import saferepr
import sys
import time
import zoneinfo

Zone_NYC = zoneinfo.ZoneInfo("America/New_York")
from datetime import datetime
from datetime import timedelta
from dateutil import parser

# from NWS_River_Data_scrape import calculated_Bushmans_river_level as get_level
from NWS_River_Data_scrape_NEW import processRiverData as get_level_data

# from NWS_River_Data_scrape_NEW import RIVER_MONITORING_POINTS
from NWS_River_Data_scrape_NEW import MCALPINE_DAM_NAME as DNRIVERDAM
from NWS_River_Data_scrape_NEW import MARKLAND_DAM_NAME as UPRIVERDAM

from pupdb.core import PupDB

# detect various add-on Rpi hats
try:
    SenseHatLoaded = True
    from sense_hat import SenseHat
    from random_colors import Set_Random_Pixels, random_to_solid

    SENSEHAT = SenseHat()
except ImportError as e:
    SenseHatLoaded = False

PUPDB_FILENAME = "SVTB-DB.json_db"
PUPDB_MRT_KEY = "MostRecentTweet"
PUPDB_MRL_KEY = "MostRecentRiverLevel"
PUPDB_MRF_KEY = "MostRecentForecastLevel"
PUPDB_ACTION_KEY = "CurrentFloodingActionLevel"
HIGHEST_OBSERVATION_TAG = "Highest  Observation:"
LATEST_OBSERVATION_TAG = "Latest  observed"
NOAA_FORECAST_TAG = "Highest  Forecast:"
OBSERVATION_TAGS = [LATEST_OBSERVATION_TAG, HIGHEST_OBSERVATION_TAG, NOAA_FORECAST_TAG]

ACTION_LABELS = [
    "No Flooding",
    "First-action",
    "Minor-flood",
    "Moderate-flood",
    "Major-flood",
]
MINIMUM_CONCERN_LEVEL = 30
TWEET_FREQUENCY = [
    18000,
    9000,
    8000,
    7000,
    6000,
    5000,
    4000,
    3600,
]  # delay time in seconds
# Time between tweets decreases as flooding increases

# ACTION_LEVELS = [21, 23, 30, 38]
# ACTION_DICT = dict(zip(ACTION_LEVELS, ACTION_LABELS))
LOCATION_OF_INTEREST = 584  # river mile marker @ Bushman's Lake


from twython import Twython, TwythonError
from dotenv import dotenv_values

TwitterCredentials = dotenv_values(".env")
TWITTER_CREDENTIALS = (
    TwitterCredentials["APP_KEY"],
    TwitterCredentials["APP_SECRET"],
    TwitterCredentials["OAUTH_TOKEN"],
    TwitterCredentials["OAUTH_TOKEN_SECRET"],
)


from os import sys, path

RUNTIME_NAME = path.basename(__file__)

from loguru import logger

logger.remove()  # stop any default logger
LOGGING_LEVEL = "INFO"


@logger.catch
def test_tweet(db):
    logger.info(f"Database object: {type(db)}")
    data = get_level_data()
    logger.info(f"get_level_data returned: {data}")
    # data contains ALL "imortant" levels
    # TODO create function to extract only 6 most relevent current,highest,eventual levels
    obsv_dict = {}
    for lbl in OBSERVATION_TAGS:
        obsv_dict.update(extract_data(data, lbl))
    # extract 1 latest observation for each dam
    logger.info(f"Observation dict: {obsv_dict}")
    latest_dict = extract_latest(obsv_dict)
    logger.info(f"{extract_guage_data(latest_dict, UPRIVERDAM)}")
    logger.info(f"{extract_guage_data(latest_dict, DNRIVERDAM)}")
    logger.info(f"Latest dict contents: {latest_dict}")
    # TODO extract 1 forecast level for each dam
    forecast_dict = extract_forecast(obsv_dict)
    logger.info(f"Forecast dict: {forecast_dict}")
    return build_tweet(data, db)


@logger.catch
def send_tweet(db, time, tweet, twttr):
    """Accept a database object, datetime object, a tweet string and a Twython object.
    Place tweet and update filesystem storage to reflect activities.
    """
    # place tweet time into longterm storage
    db.set(PUPDB_MRT_KEY, str(time))
    # place tweet into longterm storage. Keep ALL tweets keyed on timestamp
    tweetKey = f"Tweet@{time}"
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
    """Accept argument as a list of NOAA details.
    Observations from NOAA have a format discrepacy between 'Latest' entries
    and all other forms of entry. This function looks for those entries and
    'Standardizes' them.
    """
    sani = itm
    if itm[0] == "Latest":
        logger.debug(f"Raw Item from NOAA: {itm}")
        tail = itm[3:]
        sani = [itm[0], "Observation:"]
        for i in tail:
            sani.append(i)
        logger.debug(f"Sanitized item from NOAA: {sani}")
    return sani


@logger.catch
def extract_data(cleaned_map_data, lbl_str):
    """take the 'map' data dict and extract entries matching supplied label.
    We know the 'map' contains entries of observations and forecasts. Each entry
    has the name of the dam as the last item three from the end of the line.
    """
    # scan dictionary for specified observations
    observations = {}
    logger.debug(f"{cleaned_map_data=}")
    logger.info(f"Looking for: {lbl_str}")
    for key in cleaned_map_data.keys():
        logger.debug(f"Map Data Key: {key}")
        data = cleaned_map_data[key][0]
        logger.debug(f"Map Data: {data}")
        if data == lbl_str:
            logger.debug(f"Observation Tag: {data}")
            obsrv = sanitize(cleaned_map_data[key])
            observations[key] = obsrv
            logger.debug(f"Observation: {obsrv}")
        else:
            logger.debug("Not found")
    return observations


@logger.catch
def extract_forecast(obsv_data):
    """take the 'obsv' data dict and extract entries matching forecast predictions.
    We know the 'obsv' contains entries of observations and forecasts. Each entry
    has the name of the dam as the last item three from the end of the line.
    We want one prediction for each dam.
    """
    # scan dictionary for specified observations
    observations = {}
    logger.info("Scanning for Highest Forecast observations:")
    for line in obsv_data.keys():
        logger.debug(f"Observation Key: {line}")
        logger.debug(obsv_data[line])
        if obsv_data[line][0] == NOAA_FORECAST_TAG:
            logger.debug("Highest Forecast line:")
            damname = obsv_data[line][-3]
            if damname not in observations.keys():
                observations[damname] = obsv_data[line]
            if float(observations[damname][1]) < float(obsv_data[line][1]):
                observations[damname] = obsv_data[line]
            logger.debug(obsv_data[line])
    return observations


@logger.catch
def extract_latest(obsv_data):
    """take the 'obsv' data dict and extract entries matching latest predictions.
    We know the 'obsv' contains entries of observations and forecasts. Each entry
    has the name of the dam as the last item three from the end of the line.
    We want one observation of the latest level for each dam.
    """
    # scan dictionary for specified observations
    observations = {}
    logger.info("Scanning for latest observations:")
    for line in obsv_data.keys():
        logger.debug(f"Observation Key: {line}")
        logger.debug(obsv_data[line])
        if obsv_data[line][0] == LATEST_OBSERVATION_TAG:
            logger.debug("Latest Forecast line:")
            damname = obsv_data[line][-3]
            if damname not in observations.keys():
                observations[damname] = obsv_data[line]
                logger.debug(observations[damname])
    return observations


@logger.catch
def extract_guage_data(dict_data, damname):
    guage_reading = (damname, 0, 0, 0)
    if damname in dict_data.keys():
        logger.debug(f"Entry[{damname}]:{str(dict_data[damname])}")
        date = dict_data[damname][-1]
        try:
            level_obsrvd = float(dict_data[damname][1])
            milemrkr = float(dict_data[damname][-4])
            elevate = float(dict_data[damname][-2])
        except ValueError:
            logger.error(f"Did not retrieve correct data from source.")
            guage_reading = None
        else:
            guage_reading = (damname, date, level_obsrvd, milemrkr, elevate)
    return guage_reading


@logger.catch
def calculate_level(upriver, dnriver):
    """Calculate river level at point of interest"""
    (
        _upriver_name,
        upriver_date,
        upriver_level,
        upriver_milemrkr,
        upriver_elevation,
    ) = upriver
    (
        _dnriver_name,
        dnriver_date,
        dnriver_level,
        dnriver_milemrkr,
        dnriver_elevation,
    ) = dnriver
    # calculate bushmans level based on latest observation
    slope = upriver_level - dnriver_level
    elev_diff = (
        upriver_elevation - dnriver_elevation
    )  # correct for difference in elevation of guages
    slope = slope - elev_diff
    pool_length = dnriver_milemrkr - upriver_milemrkr  # determine pool size
    per_mile_slope = slope / pool_length  # calculate an average slope for the pool
    projection = (
        dnriver_milemrkr - LOCATION_OF_INTEREST
    ) * per_mile_slope + dnriver_level  # calculate projected level
    return projection


@logger.catch
def assemble_text(latest_readings_dict, forecast_data_dict, storage_db):
    """extract guage readings from dicts and calculate river slope.
    build tweet text from results.
    """
    dnriver = extract_guage_data(latest_readings_dict, DNRIVERDAM)
    upriver = extract_guage_data(latest_readings_dict, UPRIVERDAM)
    projection = calculate_level(upriver, dnriver)

    (
        upriver_name,
        upriver_date,
        upriver_level,
        _upriver_milemrkr,
        _upriver_elevation,
    ) = upriver
    (
        dnriver_name,
        dnriver_date,
        dnriver_level,
        _dnriver_milemrkr,
        _dnriver_elevation,
    ) = dnriver

    dnriver_fcst = extract_guage_data(forecast_data_dict, DNRIVERDAM)
    upriver_fcst = extract_guage_data(forecast_data_dict, UPRIVERDAM)
    forecast = calculate_level(upriver_fcst, dnriver_fcst)

    # build text of tweet
    t1 = f"Latest Observation {upriver_level}ft. {upriver_name}{upriver_date} ** "
    t2 = f"{dnriver_level}ft. {dnriver_name}{dnriver_date} ** "
    t3 = f"Calculated Level at Bushmans {projection:.2f}ft. ** Future level {forecast:.2f}ft. at {dnriver_fcst[1]} **"
    tweet = f"{t1}{t2}{t3} ::: Data source: NOAA"
    logger.info(tweet)
    logger.info(f"Length of Tweet {len(tweet)} characters.")
    # place this river level projection into longterm storage database
    storage_db.set(PUPDB_MRL_KEY, projection)
    storage_db.set(PUPDB_MRF_KEY, forecast)
    return tweet


@logger.catch
def build_tweet(rivr_conditions_dict, db):
    """takes a dictionary of river condition observations from 2 dams and builds data into a tweet."""
    tweet = ""
    # TODO put these data gathering functions in seperate functions and return named tuples of results
    # EDIT: named tuples and dataclasses are flawed. ATTRS library is the way to go.
    """ import attr
        @attr.s
        class Point3D(object):
            x = attr.ib()
            y = attr.ib()
            z = attr.ib()
    """
    # TODO (damname,observationtype,timestamp,level)
    """ import attr
        @attr.s
        class obervation_event(object):
            damname = attr.ib()
            observation_type = attr.ib()
            timestamp = attr.ib()
            river_level = attr.ib()
    """

    # TODO organize data as: currentobservation,highestforecast,eventualforecast)
    obsv_dict = {}
    for lbl in OBSERVATION_TAGS:
        logger.info(f"Searching for tag: {lbl}")
        logger.info(f"{rivr_conditions_dict=}")
        current_observations = extract_data(rivr_conditions_dict, lbl)
        logger.info(f"{current_observations=}")
        obsv_dict.update(current_observations)
    # extract 1 latest observation for each dam
    logger.debug(f"Observation dict: {obsv_dict}")
    latest_dict = extract_latest(obsv_dict)
    logger.debug(f"Latest dict contents: {latest_dict}")
    # TODO extract 1 forecast level for each dam
    forecast_dict = extract_forecast(obsv_dict)
    tweet = assemble_text(latest_dict, forecast_dict, db)
    if tweet == "":
        logger.error(f"Did not generate a tweet string.")
    return tweet


@logger.catch
def QuantifyFlooding(MOST_RECENT_LEVEL, MINIMUM_CONCERN_LEVEL):
    flooding = int(MOST_RECENT_LEVEL - MINIMUM_CONCERN_LEVEL)
    if flooding < 0:
        flooding = 0
    # value cannot exceede number of available levels
    if flooding > len(TWEET_FREQUENCY):
        flooding = len(TWEET_FREQUENCY) - 1
    return flooding


@logger.catch
def Tweet(twtr, time, db, min_time_between_tweets):
    """Create the text of a tweet to be sent."""
    DisplayMessage("Reading new river level...")
    logger.info("Getting level data...")
    data = get_level_data()
    logger.debug(f"get_level_data={data}")
    if data == []:
        logger.error(f"Did not tweet. No tweet generated. No data available.")
        logger.info(f"Recommend waiting 10 minutes to retry.")
        return 600  # return a 10 minute waittime for retry
    logger.info(f"Ready to build tweet from data of type: {type(data)}")
    logger.debug(f"tweet data: {saferepr(data)}")
    status = build_tweet(data, db)
    if len(status) > 0:
        DisplayMessage("Tweeting...")
        send_tweet(db, time, status, twtr)
    else:
        logger.error(f"Did not tweet. No tweet generated. Unknown reason.")
        logger.info(f"Recommend waiting 10 minutes to retry.")
        return 600  # return a 10 minute waittime for retry
    return min_time_between_tweets


@logger.catch
def UpdatePrediction(twtr, time, db):
    """Returns the time to wait until next tweet and Tweets if enough time has passed
    twtr = twython object for accessing Twitter
    tm = datetime obj representing current time
    db = PupDB obj for persistant storage on local machine
    """
    last_tweet_time = db.get(PUPDB_MRT_KEY)  # recover string repr of datetime obj
    prevTweet = parser.parse(last_tweet_time)  # convert back to datetime
    latest_level = db.get(PUPDB_MRL_KEY)  # recover recent level
    logger.info(f"Most recent level: {latest_level}")
    priority = QuantifyFlooding(latest_level, MINIMUM_CONCERN_LEVEL)
    logger.info(f"Priority: {priority}")
    min_time_between_tweets = TWEET_FREQUENCY[priority]
    logger.info(f"Time between Tweets: {min_time_between_tweets}")
    # check time against minimum tweet time
    logger.info(f"Time now: {time}")
    logger.info(f"Previous Tweet time: {prevTweet}")
    elapsed = time - prevTweet  # returns a timedelta object
    logger.info(f"Time since last Tweet: {elapsed}")
    logger.info(f"Total number of seconds elapsed: {elapsed.total_seconds()}")
    if elapsed.total_seconds() >= min_time_between_tweets:
        logger.info("Tweeting...")
        waitTime = Tweet(twtr, time, db, min_time_between_tweets)
    else:
        logger.info("Too soon to tweet.")
        waitTime = min_time_between_tweets - elapsed.seconds
        logger.info(f"Recommend waiting {waitTime} seconds.")
    latest_level = db.get(PUPDB_MRL_KEY)  # recover recent level
    return (waitTime, latest_level)


@logger.catch
def DisplayMessage(message):
    global SENSEHAT
    if SenseHatLoaded:
        # TODO add additonal data like temp and humidity of server hat
        SENSEHAT.show_message(message)
        time.sleep(1)
        # TODO monitor joystick input to exit pixel display early
        lastColor = Set_Random_Pixels(SENSEHAT)
        random_to_solid(SENSEHAT, colorName=lastColor, fast=True)
    return True


@logger.catch
def DetermineTrend(now, soon):
    """returns text describing if the trend of the river is rising or falling.
    now = float value of current level of river
    soon = float value of future level of river
    """
    if now > soon:
        return "Falling"
    if now < soon:
        return "Rising"
    return "Flat"


@logger.catch
def AreWeThereYet(wait, new_level, trend):
    """returns how much longer to wait until next report should be generated.
    wait = int: number of seconds to wait
    This function updates any attached displays and then returns a new wait time.
    """
    startDisplay = int(time.time())
    time.sleep(5)  # guarantee at least a 5 second pause
    if (
        startDisplay % 10
    ) == 0:  # update external displays connected to server each ten seconds.
        DisplayMessage(
            f"  {new_level:.2f}ft Latest. Trend: {trend}   Now {new_level:.2f}ft   Trend: {trend}"
        )
    endDisplay = int(time.time())
    elapsed = endDisplay - startDisplay
    return wait - elapsed


@logger.catch
def ActivateDatabase(PupDB_FILENAME, TimeNow):
    # TODO place db functions into its own function
    storage_db = PupDB(PupDB_FILENAME)
    last_tweet = storage_db.get(PUPDB_MRT_KEY)
    last_level = storage_db.get(PUPDB_MRL_KEY)
    if last_tweet is None:  # Pre-load empty database
        last_tweet = str(TimeNow)
        last_level = MINIMUM_CONCERN_LEVEL
        storage_db.set(PUPDB_MRT_KEY, last_tweet)
        storage_db.set(PUPDB_MRL_KEY, last_level)
        forecast_level = last_level
        storage_db.set(PUPDB_MRF_KEY, forecast_level)
    return storage_db


@logger.catch
def Main(credentials):
    defineLoggers()
    logger.info(f"Sense Hat loaded: {SenseHatLoaded}")
    # unpack the credentials before submitting to Twython
    a, b, c, d = credentials
    # establish the twitter access object
    twitter = Twython(a, b, c, d)
    # activate PupDB file for persistent storage
    TimeNow = datetime.now()
    storage_db = ActivateDatabase(PUPDB_FILENAME, TimeNow)
    # initialization complete. Begin main loop.
    while True:
        TimeNow = datetime.now()
        wait, new_level = UpdatePrediction(twitter, TimeNow, storage_db)
        forecast_level = storage_db.get(PUPDB_MRF_KEY)
        trend = DetermineTrend(new_level, forecast_level)
        logger.info(f"New wait time: {wait}")
        logger.info(f"New Level: {new_level}")
        logger.info(f"Trend: {trend}")
        nextTweet = TimeNow + timedelta(0, wait)
        logger.info(f"Next tweet at {nextTweet}")
        while wait > 1:
            wait = wait - 55
            time.sleep(55)
            if datetime.now() > nextTweet:
                logger.info(f"{wait} seconds left but tweet time has passed.")
                wait = 0
    return


@logger.catch
def defineLoggers():
    logger.add(
        sys.stderr,
        colorize=True,
        format="<green>{time}</green> {level} <blue>{message}</blue>",
        level=LOGGING_LEVEL,
    )
    logger.add(  # create a new log file for each run of the program
        "./LOGS/" + RUNTIME_NAME + "_{time}.log",
        retention="10 days",
        # compression="zip",
        level="DEBUG",  # always send debug output to file
    )
    logger.add(  # create a log file for each run of the program
        "./LOGS/" + RUNTIME_NAME + ".log",
        retention="10 days",
        # compression="zip",
        level="DEBUG",  # always send debug output to file
    )
    return


if __name__ == "__main__":
    Main(TWITTER_CREDENTIALS)

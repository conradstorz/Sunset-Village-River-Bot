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

from loguru import logger
logger.remove()  # stop any default logger
LOGGING_LEVEL = "INFO"

from NWS_River_Data_scrape import calculated_Bushmans_river_level as get_level
from NWS_River_Data_scrape_NEW import processRiverData as get_level_data
from NWS_River_Data_scrape_NEW import RIVER_MONITORING_POINTS
from NWS_River_Data_scrape_NEW import MCALPINE_DAM_NAME as DNRIVERDAM
from NWS_River_Data_scrape_NEW import MARKLAND_DAM_NAME as UPRIVERDAM
from pprint import saferepr
from pprint import pprint

from pupdb.core import PupDB

PupDB_FILENAME = "SVTB-DB.json_db"
PupDB_MRTkey = "MostRecentTweet"
PupDB_MRLkey = "MostRecentRiverLevel"
PupDB_ACTIONkey = "CurrentFloodingActionLevel"

ACTION_LABELS = ["No Flooding", "First-action", "Minor-flood", "Moderate-flood", "Major-flood"]
TWEET_FREQUENCY = [18000, 9000, 4000, 2000, 1000] # delay time in seconds
#ACTION_LEVELS = [21, 23, 30, 38]
#ACTION_DICT = dict(zip(ACTION_LEVELS, ACTION_LABELS))
LOCATION_OF_INTEREST = 584  # river mile marker @ Bushman's Lake


from twython import Twython, TwythonError
from TwitterCredentials import APP_KEY
from TwitterCredentials import APP_SECRET
from TwitterCredentials import OAUTH_TOKEN
from TwitterCredentials import OAUTH_TOKEN_SECRET

TWITTER_CREDENTIALS = (APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
#MAXIMUM_TWEETS_PER_HOUR = 0.2
MINIMUM_TIME_BETWEEN_TWEETS = TWEET_FREQUENCY[0]

from os import sys, path

RUNTIME_NAME = path.basename(__file__)


@logger.catch
def test_tweet():
    data = get_level_data()
    return build_tweet(data)


@logger.catch
def send_tweet(tweet, twttr):
    twttr.update_status(status=tweet)
    logger.info("Tweet sent.")
    logger.debug("Tweet string = " + str(tweet))
    logger.info("Length of string = " + str(len(tweet)))
    return True


@logger.catch
def check_if_time_to_tweet(river_dict, tm, twttr, pdb):
    """ Check if it is time to tweet
    updates PupDB storage, 
    monitors flooding condition and updates time between tweets based on action level.
    """
    # check time
    MOST_RECENT_TWEET = pdb.get(PupDB_MRTkey)  # recover string repr of datetime obj
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
        # build tweet
        message = build_tweet(river_dict)
        # send tweet
        send_tweet(message, twttr)
        pdb.set(PupDB_MRTkey, str(tm))       
    # update action level
    current_action = pdb.get(PupDB_ACTIONkey)
    most_recent_level = pdb.get(PupDB_MRLkey)
    for action in ACTION_LABELS:
        for dam in RIVER_MONITORING_POINTS.keys():
            level = RIVER_MONITORING_POINTS[dam][action]
            if level <= most_recent_level:
                current_action = action
    pdb.set(PupDB_MRLkey, str(current_action))
    # return time to next tweet
    logger.info("Too soon to tweet.")
    waitTime = MINIMUM_TIME_BETWEEN_TWEETS - elapsed.seconds
    logger.info("Recommend waiting " + str(waitTime) + " seconds.")
    return waitTime


@logger.catch
def build_tweet(rivr_conditions_dict):
    """takes a dictionary of river condition observations from 2 dams and builds data into a tweet,
    """
    tweet = " "
    # scan dictionary for latest observations
    latest_observations = []
    for line in rivr_conditions_dict.keys():
        if rivr_conditions_dict[line][0] == "Latest":
            latest_observations.append(rivr_conditions_dict[line])
    logger.debug('latest[0]:' + str(latest_observations[0]))
    logger.debug('latest[1]:' + str(latest_observations[1]))
    # scan dictionary for Forecast observations
    forecast_observations = []
    forecast_dict = {}
    for key in rivr_conditions_dict.keys():
        if rivr_conditions_dict[key][0] == "Highest":
            forecast_observations.append(rivr_conditions_dict[key])
    # scan results
    for index, item in enumerate(forecast_observations):
        # report findings to DEBUG logger    
        logger.debug(f'forecast[{index}]:{str(item)}')
        # isolate the highest forecast for each dam
        dam_name = item[-3]
        if dam_name not in forecast_dict:
            forecast_dict[dam_name] = item
        else:
            # check to see if this forecast is higher than the one already located
            level1 = float(item[2])
            dam_details = forecast_dict[dam_name]
            level2 = float(dam_details[2])
            if level1 > level2:
                # it is so replace the lower one
                forecast_dict[dam_name] = item
    for key in forecast_dict.keys():
        logger.debug(f'forecast[{key}]:{str(forecast_dict[key])}')
        level_forecast = float(forecast_dict[key][2])
        if key == UPRIVERDAM:
            upriver_forecast = level_forecast
        if key == DNRIVERDAM:
            dnriver_forecast = level_forecast
        forecast_timestamp = forecast_dict[key][-1]
    # gather needed numbers
    upriver_name = latest_observations[1][-3]
    upriver_level = float(latest_observations[1][3])
    upriver_milemrkr = float(latest_observations[1][-4])
    upriver_elevation = float(latest_observations[1][-2])
    dnriver_name = latest_observations[0][-3]
    dnriver_level = float(latest_observations[0][3])
    dnriver_milemrkr = float(latest_observations[0][-4])
    dnriver_elevation = float(latest_observations[0][-2])
    obsrv_datetime = latest_observations[0][-1]
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
    # calculate bushmans level forecast to occur soon
    forecast_slope = upriver_forecast - dnriver_forecast
    forecast_slope = forecast_slope - elev_diff
    # calculate an average slope for the pool
    forecast_per_mile_slope = forecast_slope / pool_length
    # calculate projected level
    forecast_projection = (
        dnriver_milemrkr - LOCATION_OF_INTEREST
    ) * forecast_per_mile_slope + dnriver_forecast
    # build text of tweet
    t1 = f"Latest Observation: {obsrv_datetime} {upriver_name}"
    t2 = f" {upriver_level} {dnriver_name} {dnriver_level}"
    t3 = f" Calculated Level at Bushmans: {projection:.2f}"
    t4 = f" ::: Latest Forecast: {upriver_name} {upriver_forecast}"
    t5 = f" {dnriver_name} {dnriver_forecast}"
    t6 = f" Calculated future Level at Bushmans: {forecast_projection:.2f} {forecast_timestamp}"    
    tweet = t1 + t2 + t3 + t4 + t5 + t6
    logger.info(tweet)
    logger.info(f'Length of Tweet {len(tweet)} characters.')
    return tweet


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
        # x = get_level()  # retrieve river level readings
        # sp = saferepr(x)  # use pprint to serialize a version of the result
        # 12-17-2019 using new method
        data = get_level_data()
        sp = build_tweet(data)        
        db.set(PupDB_MRTkey, str(tm))
        twtr.update_status(status=sp)
        logger.info("Tweet sent.")
        logger.debug("Tweet string = " + str(sp))
        # 12-17-2019 new method logs this in the build tweet routine
        # for item in x:
        #     logger.info(item)
        # logger.info("Length of string = " + str(len(sp)))
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

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

import sys
from NWS_River_Data_scrape import calculated_Bushmans_river_level as get_level
from pprint import saferepr
from pprint import pprint

from pupdb.core import PupDB
PupDB_FILENAME = 'SVTB-DB.json_db'
PupDB_MRTkey = 'M_R_Tweet'

from twython import Twython, TwythonError
from TwitterCredentials import APP_KEY
from TwitterCredentials import APP_SECRET
from TwitterCredentials import OAUTH_TOKEN
from TwitterCredentials import OAUTH_TOKEN_SECRET
TWITTER_CREDENTIALS = (APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
MAXIMUM_TWEETS_PER_HOUR = 1
MINIMUM_TIME_BETWEEN_TWEETS = 3600 / MAXIMUM_TWEETS_PER_HOUR # in seconds

TWEET_GLOBALS = { #TODO make this a list of times and have tweet function limit number of tweets per hour
                    #TODO also... make the frequency go up when flooding is significant. Use the action levels of McAlpine dam as indicators of needed frequency
                    #TODO make twittrbot interactive with users by allowing them to tweet a mile marker they want monitored and add it to the outgoing tweets for a period of 30 days. must be between markland and mcalpine for this bot.
    "MorningTweetTime": 6, #hour
    "MorningTweet": False,  # has morning tweet occured
    "EveningTweetTime": 18, #hour
    "EveningTweet": False,
    "SleepInterval": 1200,  # 20 minutes
}


def UpdatePrediction(twtr, tm):
    waitTime = 0
    x = get_level() #retrieve river level readings
    sp = saferepr(x) #use pprint to serialize a version of the result
    # TODO Check for valid tweet time by limit of number of tweets per hour.
    MOST_RECENT_TWEET = storage_db.get(PupDB_MRTkey) # recover string repr of datetime obj
    prevTweet = parser.parse(MOST_RECENT_TWEET) # convert back to datetime
    # check tm against minimum tweet time
    elapsed = tm - prevTweet # returns a timedelta object
    if elapsed.seconds >= MINIMUM_TIME_BETWEEN_TWEETS:
        print("Tweeting...")
        storage_db.set(PupDB_MRTkey, tm)
        twtr.update_status(status=sp)
        print("Tweet sent.")
        # print('results = ',sp)
        for item in x:
            print(item)
        print("Length of string = ", len(saferepr(x)))
    else:
        print('Too soon to tweet.')
        waitTime = MINIMUM_TIME_BETWEEN_TWEETS - elapsed.seconds
        print('Reccomend waiting', waitTime, 'seconds.')
    return waitTime


def Main(credentials, params):

    # unpack the credentials before submitting to Twython
    a, b, c, d = credentials

    # establish the twitter access object
    twitter = Twython(a, b, c, d)

    # activate PupDB file for persistent storage
    strTimeNow = str(datetime.now())
    storage_db = PupDB(PupDB_FILENAME)
    MOST_RECENT_TWEET = storage_db.get(PupDB_MRTkey)
    if MOST_RECENT_TWEET == None: # Pre-load empty database
        storage_db.set(PupDB_MRTkey, strTimeNow)

    while True:
        strTimeNow = str(datetime.now())

        TimeNow = time.localtime(time.time()).tm_hour
        print("Checking time...", strTimeNow)

        if params["MorningTweet"] != True:
            if TimeNow == params["MorningTweetTime"]:
                params["MorningTweet"] = True
                params["EveningTweet"] = False
                UpdatePrediction(twitter, strTimeNow)

        if params["EveningTweet"] != True:
            if TimeNow == params["EveningTweetTime"]:
                params["EveningTweet"] = True
                params["MorningTweet"] = False
                UpdatePrediction(twitter, strTimeNow)

        print("Time to sleep", params["SleepInterval"], "seconds")
        time.sleep(params["SleepInterval"])
    return
"""
 pseudo code notes:
    while True:
        TimeNow = time.localtime(time.time()).tm_hour
        log("Checking time...")
        if time in timestotweet:
            log("its a tweet'n time!")
            updateprediction(twitter)
        log("sleeping")
        sleep(areasonabletime)
    
    def UpdatePrediction(twtr):
        if tweetsthishour <= MAXIMUM_TWEETS_PER_HOUR:
            log("getting readings")
            x = get_level() #retrieve river level readings
            sp = safeprint(x) #use pprint to serialize a version of the result
            log("Tweeting...")
            twtr.update_status(status=sp)
            log("Tweet sent.")
            log('results = ',sp)
            for item in x:
                log(item)
            log("Length of string = ", len(safeprint(x)))
        else:
            log("tweets per hour maximum reached")
        return
"""

if __name__ == "__main__":
    Main(TWITTER_CREDENTIALS, TWEET_GLOBALS)

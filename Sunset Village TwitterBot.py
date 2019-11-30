#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This is a twitterBot that will periodically tweet the projected river level at Bushman's Lake based on the 
NWS website data for the river level both upstream and downstream then calculating the slope of the river
to get the calculated level at our property. 
"""

from twython import Twython, TwythonError
import time
from datetime import datetime, timezone
import sys
from NWS_River_Data_scrape import calculated_Bushmans_river_level as get_level
from pprint import saferepr as safeprint
from pprint import pprint

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


def UpdatePrediction(twtr):
    x = get_level() #retrieve river level readings
    sp = safeprint(x) #use pprint to serialize a version of the result
    # TODO Check for valid tweet time by limit of number of tweets per hour.
    # TODO Use a file stored on this server to track last time tweet was sent.
    print("Tweeting...")
    twtr.update_status(status=sp)
    print("Tweet sent.")
    # print('results = ',sp)
    for item in x:
        print(item)
    print("Length of string = ", len(safeprint(x)))
    return # TODO Return the number of seconds before next available tweet window


def Main(credentials, params):

    # unpack the credentials before submitting to Twython
    a, b, c, d = credentials

    # establish the twitter access object
    twitter = Twython(a, b, c, d)

    while True:
        TimeNow = time.localtime(time.time()).tm_hour

        print("Checking time...", datetime.now().strftime("%m/%d/%Y, %H:%M"))

        if params["MorningTweet"] != True:
            if TimeNow == params["MorningTweetTime"]:
                params["MorningTweet"] = True
                params["EveningTweet"] = False
                UpdatePrediction(twitter)

        if params["EveningTweet"] != True:
            if TimeNow == params["EveningTweetTime"]:
                params["EveningTweet"] = True
                params["MorningTweet"] = False
                UpdatePrediction(twitter)

        print("Time to sleep", params["SleepInterval"], "seconds")
        time.sleep(params["SleepInterval"])
    return
"""
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

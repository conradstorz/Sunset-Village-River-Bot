#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Test the operation of elements of the TwittetBot code
"""

from Sunset_Village_TwitterBot import test_tweet, defineLoggers
from loguru import logger
from pupdb.core import PupDB

# create a dummy data file database
storage_db = PupDB("temp")
defineLoggers()
print("tweet:", test_tweet(storage_db))

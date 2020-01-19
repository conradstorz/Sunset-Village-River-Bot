#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Test the operation of elements of the TwittetBot code
"""

from Sunset_Village_TwitterBot import test_tweet, defineLoggers
from loguru import logger

defineLoggers()
print('tweet:', test_tweet())
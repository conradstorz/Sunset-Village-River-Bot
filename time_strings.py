#!/usr/bin/env python
# -*- coding: utf-8 -*-
# version 2.0
"""Standardize time strings and datetime objects used in a project.
"""


from datetime import datetime, date, timezone, timedelta
from time import sleep
import pytz
from loguru import logger


tz_UTC = pytz.timezone("UTC")
tz_LOCAL = pytz.timezone("America/Louisville")


@logger.catch
def timefstring(dtobj, tz_name=True):
    """Standardize the format used for timestamp string format.
    Include 3 letter string for timezone if set to True.
    """
    if tz_name:
        return f'{dtobj.strftime("%Y-%m-%d_%H:%M:%S%Z")}'
    else:
        return f'{dtobj.strftime("%Y-%m-%d_%H:%M:%S")}NTZ' #NTZ = Naive Time Zone


def LOCAL_TODAY():
    return  date.today()

def UTC_NOW():
    return datetime.now(tz_UTC)

def LOCAL_CURRENT_YEAR():
    return str(LOCAL_TODAY().year)

def LOCAL_TODAY_STRING():
    return LOCAL_TODAY().strftime("%Y-%m-%d")

def UTC_NOW_STRING():
    return timefstring(UTC_NOW())

def LOCAL_NOW():
    return datetime.now(tz_LOCAL)

def LOCAL_NOW_STRING():
    return timefstring(LOCAL_NOW())


if __name__ == "__main__":
    for i in range(5):
        print(f"LOCAL TODAY: {LOCAL_TODAY()} type: {type(LOCAL_TODAY())}")
        print(f"UTC NOW: {UTC_NOW()} type: {type(UTC_NOW())}")
        print(f"LOCAL NOW: {LOCAL_NOW()} type: {type(LOCAL_NOW())}")
        print(f"LOCAL CURRENT_YEAR: {LOCAL_CURRENT_YEAR()} type: {type(LOCAL_CURRENT_YEAR())}")
        print(f"LOCAL TODAY_STRING: {LOCAL_TODAY_STRING()} type: {type(LOCAL_TODAY_STRING())}")
        print(f"UTC NOW_STRING: {UTC_NOW_STRING()} type: {type(UTC_NOW_STRING())}")
        print(f"LOCAL NOW_STRING: {LOCAL_NOW_STRING()} type: {type(LOCAL_NOW_STRING())}")
        sleep(2)
        print()


def apply_logical_year_value_to_monthday_pair(datestring, scrape_datestamp):
    """Given a month and day apply the rule that it must represent a day in the near past or future.
    This problem presents itself when gathering data from the National Weather Service.
    The site I am scraping for the readings of river water level values does only include the month/day not year.
    These datapoints are historical going back only approximately 30 days and forecast only 7 days future.
    At the end of a year and the first month of the year they are problematic.

    Args:
        datestring (str): 'any parseable string representing a month and day'
        scrape_datestamp (datetime.datetime):  actual date of web scrape.

    Returns:
        datetime.object: fully qualified date with the corrected year.
    """
    from dateutil.parser import parse, ParserError
    try:
        supplied_date = parse(datestring)
    except ParserError as e:
        print(f'{e}: Could not parse datestring provided.')
        raise ParserError(e)

    # All work is done with timezone aware objects.
    supplied_date = supplied_date.replace(tzinfo=pytz.UTC)
    scrape_datestamp = scrape_datestamp.replace(tzinfo=pytz.UTC)

    # expceted result: type datetime(yyyy, mm, dd, hh, min, sec) object
    sc_yyyy = scrape_datestamp.strftime("%Y")
    su_mnth = supplied_date.strftime("%m")
    su_dy = supplied_date.strftime("%d")

    if len(sc_yyyy)+len(su_mnth)+len(su_dy) != 8 or not(f'{sc_yyyy}{su_mnth}{su_dy}'.isdigit()):
        print(f'Parsed date returned y={sc_yyyy} m={su_mnth} d={su_dy}')
        raise AttributeError('Argument must be a parseable datestring.')

    offered_year = int(sc_yyyy)
    prev_year = offered_year-1
    next_year = offered_year+1

    mm = int(su_mnth)
    dd = int(su_dy)

    # Create a UTC timezone instance
    UTC_TimeDelta = timedelta(hours=0)
    tzUTC = timezone(UTC_TimeDelta, name="UTC")

    # create list of possible dates
    dates = []
    offered_datestamp = datetime(offered_year,mm,dd,1,0,0,0,tzUTC)
    dates.append(offered_datestamp)
    prev_datestamp = datetime(prev_year,mm,dd,1,0,0,0,tzUTC)
    dates.append(prev_datestamp)
    next_datestamp = datetime(next_year,mm,dd,1,0,0,0,tzUTC)
    dates.append(next_datestamp)

    # Create a dict of dates keyed on the number of days elapsed.
    delta_dict = {}
    for _i, date in enumerate(dates):
        delta = scrape_datestamp - date
        # print(f'{scrape_datestamp} scrape, {date} date')
        delta_dict[abs(delta.days)] = date

    # Sort and return only the date nearest in time to year specified.
    keys = sorted(delta_dict.keys())
    corrected_datestamp = delta_dict[keys[0]]

    # print(f'Offered:{datestring} and scrape year {scrape_datestamp}, Corrected:{corrected_datestamp}')    
    # print(f'{delta_dict}')

    return corrected_datestamp




# Notes:
"""
# working with datetime objects:

#    It is allowed to subtract one datetime object from another datetime object
#    The resultant object from subtraction of two datetime objects is an object of type timedelta

import datetime

d1 = datetime.datetime.now()
d2 = datetime.datetime.now()
x  = d2-d1
print(type(x))
print(x)
 
    Output:
        <class 'datetime.timedelta'>
        0:00:00.000008

#    The subtraction operation of two datetime objects succeeds, if both the objects are naive objects, 
#    or both the objects are aware objects. i.e., Both the objects have their tzinfo as None
#    If one datetime object is a naive object and another datetime object is an aware object 
#    then  python raises an exception of type TypeError stating:
#       TypeError: can't subtract offset-naive and offset-aware datetimes.

import datetime
# Time difference for pacific time
pacificTimeDelta    = datetime.timedelta(hours=-8)

# Create a PST timezone in instance
tzPST        = datetime.timezone(pacificTimeDelta, name="PST")

# create a datetime for 1 PM PST - 31Dec2017 - An aware Object
OnePMyearEndPST = datetime.datetime(2017,12,31,1,0,0,0,tzPST)

# create a dateobject for current time - without any timezone attached - A naive object
todaysDate = datetime.datetime.now()

# Try subtracting the naive object from the aware object
    # This will raise a Type Error
todaysDate = OnePMyearEndPST - todaysDate
    TypeError: can't subtract offset-naive and offset-aware datetimes

# Time difference for EST time
nycTimeDelta    = datetime.timedelta(hours=-8)

# Create a PST timezone in instance
tzEST           = datetime.timezone(nycTimeDelta, name="EST")

# create a datetime for 1 PM PST - 31Dec2017 - An aware Object
TwoPMyearEndEST = datetime.datetime(2017,12,31,2,0,0,0,tzEST)

# If both the datetime objects are aware objects and each object is having a different time zone information 
#   – then both the time quantity of the objects are converted into UTC first 
#       and the subtraction is applied on the two UTC time quantities.
print(TwoPMyearEndEST-OnePMyearEndPST)
    Output:
        1:00:00



"""
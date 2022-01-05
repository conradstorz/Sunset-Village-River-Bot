#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This file contains code that can scrape the National Weather Service (NWS) website and read the 
river level data for both Markland and McAlpine dams. By using the mileage marker for Bushman's Lake 
the level of the river at that point can be calculated.
"""
# from tabulate import tabulate

from loguru import logger

LOGGING_LEVEL = "INFO"

from os import sys, path
from datetime import datetime, timezone
from dateutil import parser as dateparser
# from dateutil.utils import default_tzinfo
# import datefinder
from dateparser.search import search_dates

from pprint import saferepr
# from pprint import pprint

import cfsiv_utils.WebScraping as ws
# from WebScraping import retrieve_cleaned_html
from lxml import etree as ET


RUNTIME_NAME = path.basename(__file__)
Data_datestamp = datetime.now()

ACTION_LABELS = ["First-action", "Minor-flood", "Moderate-flood", "Major-flood"]

MARKLAND_DAM_URL = "https://water.weather.gov/ahps2/hydrograph.php?wfo=iln&gage=mklk2"
MARKLAND_DAM_NAME = "Markland"

MCALPINE_DAM_URL = "https://water.weather.gov/ahps2/hydrograph.php?gage=mluk2&wfo=lmk"
MCALPINE_DAM_NAME = "McAlpine"

MCALPINE_DAM_DETAILS = {
    "Friendly_Name": "McAlpine Dam Upper Guage",
    "Dam_URL": MCALPINE_DAM_URL,
    "milemarker": 606.8,
    "guage_elevation": 407.18,
    ACTION_LABELS[0]: 21,
    ACTION_LABELS[1]: 23,
    ACTION_LABELS[2]: 30,
    ACTION_LABELS[3]: 38,
}

MARKLAND_DAM_DETAILS = {
    "Friendly_Name": "Markland Dam Lower Guage",
    "Dam_URL": MARKLAND_DAM_URL,
    "milemarker": 531,
    "guage_elevation": 408,
    ACTION_LABELS[0]: 49,
    ACTION_LABELS[1]: 51,
    ACTION_LABELS[2]: 62,
    ACTION_LABELS[3]: 74,
}

RIVER_MONITORING_POINTS = {
    MCALPINE_DAM_NAME: MCALPINE_DAM_DETAILS,
    MARKLAND_DAM_NAME: MARKLAND_DAM_DETAILS,
}

DAMS = list(RIVER_MONITORING_POINTS.keys())
IMPORTANT_OBSERVATIONS = ["Forecast:", "Latest", "Highest"]


@logger.catch
def ISO_datestring(dt, cl):
    """ Convert a DateTime object to an ISO datestring.
    also fix an error in the conversion
    .isoformat() returns 12:00:00 for both Noon and Midnight.
    Also trim date to report only date, hours and minutes.
    """
    isodatestr = dt.isoformat()
    if cl[4] == "12:00AM":  # reset time to 00:00 since it incorrectly gets set to 12:00
        isodatestr = isodatestr[0:11] + "00:00"
    else:
        isodatestr = isodatestr[0:16]  # just slice off seconds and timezone
    return isodatestr


@logger.catch
def current_river_conditions(monitoring_point, dct):
    """ scrape NOAA website for current river conditions.
    Write results to PupDB file and include current flooding action level
    """
    # TODO this routine is too fragile and needs better error handling
    this_river = RIVER_MONITORING_POINTS[monitoring_point]
    logger.info("Scraping webite..." + saferepr(this_river["Friendly_Name"]))
    html = ws.retrieve_cleaned_html(this_river["Dam_URL"])
    if html != None:
        logger.info('...scanning list of "map" objects...')
        map_raw = html.select("map")[0]  # grab first item named 'map'
    else:
        logger.error(
            f'No "HTML" returned in web scrape of {this_river["Friendly_Name"]}'
        )
        return {}  # error condition
    parser_engine = ET.XMLParser(recover=True)
    tree = ET.fromstring(str(map_raw), parser=parser_engine)
    root = tree.getroottree()
    root_map = root.getroot()
    logger.debug("map name: " + saferepr(root_map.attrib["name"]))
    map_dict = dct

    for child in root_map:
        # logger.debug("root_map_child tag: " + saferepr(child.tag))
        try:
            child_list = child.attrib["alt"].split()
            child_list.append(RIVER_MONITORING_POINTS[monitoring_point]["milemarker"])
            child_list.append(monitoring_point)
            child_list.append(
                RIVER_MONITORING_POINTS[monitoring_point]["guage_elevation"]
            )
            # logger.debug("Raw 'attrib' 'alt': " + saferepr(child.attrib["alt"]))
            searchdate = search_dates(child.attrib["title"], languages=["en"])
            if type(searchdate) == list:
                child_date = searchdate[0][1]
                date_iso = ISO_datestring(child_date, child_list)
                child_list.append(date_iso)
                # logger.debug("datestamp search result:" + str(date_iso))
                if date_iso in map_dict:
                    # should only happen if two observations have the same datestamp
                    logger.error("duplicate key!")  # TODO raise dupkey error
                    logger.debug("Raw 'attrib' 'alt': " + saferepr(child.attrib["alt"]))
                    logger.debug("datestamp search result:" + str(date_iso))
                    logger.debug(saferepr(child_list))
                    sys.exit(1)
                else:
                    observation_key = date_iso + monitoring_point
                    map_dict[observation_key] = child_list
            else:
                logger.debug("no date found")
                logger.debug("Raw 'attrib' 'alt': " + saferepr(child.attrib["alt"]))
                logger.debug(f"datestamp search result:{type(searchdate)}")
                logger.debug(saferepr(child.attrib))
        except ValueError as e:
            logger.debug("no date")
            logger.debug("child element result:" + str(child))
            logger.debug(saferepr(e))
        except KeyError:
            logger.debug("no title")
            logger.debug("child element result:" + str(child))
    logger.debug(f"Current_River_Conditions function results: {saferepr(map_dict)}")
    return map_dict


@logger.catch
def clean_item(lst):
    """ Remove a specified list of items from list and combine some items.
    """
    try:
        float(lst[1])
    except ValueError:
        # combine first and second items
        tag = f"{lst[0]}  {lst[1]}"
        if lst[2] == "value:":
            # drop bad label
            lst = lst[3:]
        else:
            lst = lst[2:]
        lst.insert(0, tag)
    for item in ["at", "EST", "Flood", "Stage", "is", "ft"]:
        lst = [s for s in lst if s != item]
    if lst[3] in ["AM", "PM"]:
        lst[2] = f"{lst[2]}{lst[3]}"
    return lst


@logger.catch
def processRiverData():
    """get current data from NOAA website.
    Organize data as dictionary keyed by timestamps+damname.
    """
    logger.info("Program Start: " + RUNTIME_NAME)
    results = {}
    for name in DAMS:
        results = current_river_conditions(name, results)
    if results == {}:
        return []  # error condition
    times = list(results.keys())
    times = sorted(times)
    output = {}
    for item in times:
        if results[item][0] in IMPORTANT_OBSERVATIONS:
            logger.debug(f"Raw item: {saferepr(results[item])}")
            sani = clean_item(results[item])
            logger.debug(f"Cleaned item: {sani}")
            output[item] = sani
    return output


@logger.catch
def defineLoggers():
    logger.remove()  # stop any default logger    
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


@logger.catch
def MAIN():
    defineLoggers()
    # print(tabulate(processRiverData()))
    map_data = processRiverData()
    if map_data == []:
        return False  # error condition
    for item in map_data:
        print(item, map_data[item])
    return True


if __name__ == "__main__":
    result = MAIN()
    if result == True:
        logger.info("Program ended normally.")
    else:        
        logger.info("Program ended abnormally.")   

""" This file contains code that can scrape the Nation Weather Service (NWS) website and read the 
river level data for both Markland and McAlpine dams. By using the mileage marker for Bushman's Lake 
the level of the river at that point can be calculated.
"""

import sys

from loguru import logger

logger.remove()  # stop any default logger
LOGGING_LEVEL = "DEBUG"

from os import sys, path
from datetime import datetime, timezone
from dateutil import parser as dateparser
from dateutil.utils import default_tzinfo
import datefinder
from dateparser.search import search_dates

from pprint import saferepr
from pprint import pprint

from WebScraping import retrieve_cleaned_html
from lxml import etree as ET


RUNTIME_NAME = path.basename(__file__)
Data_datestamp = datetime.now()

ACTION_LABELS = ["First-action", "Minor-flood", "Moderate-flood", "Major-flood"]

MCALPINE_DAM_URL = "https://water.weather.gov/ahps2/hydrograph.php?wfo=iln&gage=mklk2"
MCALPINE_DAM_NAME = "McAlpine"
MCALPINE_DAM_DETAILS = {
    "Dam_URL": MCALPINE_DAM_URL,
    "milemarker": 606.8,
    "guage_elevation": 407.18,
    ACTION_LABELS[0]: 21,
    ACTION_LABELS[1]: 23,
    ACTION_LABELS[2]: 30,
    ACTION_LABELS[3]: 38,
}

MARKLAND_DAM_URL = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=142935&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=hydrograph"
MARKLAND_DAM_NAME = "Markland"
MARKLAND_DAM_DETAILS = {
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


@logger.catch
def ISO_datestring(dt, cl):
    """ Convert a DateTime object to an ISO datestring.
    also fix an error in the conversion
    .isoformat() returns 12:00:00 for both Noon and Midnight
    """
    isodatestr = dt.isoformat()
    if (
        cl[4] == "12:00AM"
    ):  # reset time to 00:00:00 since it incorrectly gets set to 12:00:00
        isodatestr = isodatestr[0:11] + "00:00:00"
    return isodatestr


@logger.catch
def current_river_conditions(monitoring_point, dct):
    """ scrape NOAA website for current river conditions.
    Write results to PupDB file and include current flooding action level
    """
    html = retrieve_cleaned_html(RIVER_MONITORING_POINTS[monitoring_point]["Dam_URL"])
    print('...begin list of "map" objects...')
    map_raw = html.select("map")[0]  # grab first item named 'map'
    parser_engine = ET.XMLParser(recover=True)
    tree = ET.fromstring(str(map_raw), parser=parser_engine)
    root = tree.getroottree()
    root_map = root.getroot()
    # print(root_map) #logger debug
    map_dict = dct
    for child in root_map:
        # print('root_map_child tag: ', child.tag)#logger debug
        try:
            child_list = child.attrib["alt"].split()
            child_list.append(monitoring_point)
            # print("=== root_map_child attrib: ", child_list)#logger debug
            # print(child.attrib["alt"])#logger debug
            searchdate = search_dates(child.attrib["title"], languages=["en"])
            if type(searchdate) == list:
                child_date = searchdate[0][1]  # TODO append dt obj to child_list
                date_iso = ISO_datestring(
                    child_date, child_list
                )  # TODO append datestr to child_list
                # print("search:", type(child_date), date_iso)
                if date_iso in map_dict:
                    logger.error("duplicate key!")  # TODO raise dupkey error
                    logger.error(child_list)
                else:
                    observation_key = date_iso + monitoring_point
                    map_dict[observation_key] = child_list
            else:
                logger.error("no date found")
                logger.error(child.attrib)
        except ValueError as e:
            logger.error("no date")
            logger.error(e)
        except KeyError:
            logger.error("no title")
            logger.error(child.attrib)
    # pprint(map_dict)
    return map_dict


@logger.catch
def processRiverData():
    """get current data from NOAA website and return conditions including flood action levels
    """
    logger.info("Program Start: " + RUNTIME_NAME)
    results = {}
    for name in DAMS:
        results = current_river_conditions(name, results)
    times = list(results.keys())
    times = sorted(times)
    important = ["Forecast:", "Latest", "Highest"]
    for item in times:
        if results[item][0] in important:
            print(results[item])
    return results  # TODO define a dict of dams and important observations


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
        level="DEBUG",  # always send debug output to file
    )
    return


@logger.catch
def MAIN():
    defineLoggers()
    processRiverData()
    return True


if __name__ == "__main__":
    MAIN()
"""    
'Observed'
'Forecast:'
'Latest'
'Highest'
['Highest', 'Observation:', '12.99', 'ft', 'at', '1:35AM', 'Dec', '02,', '2019', 'Markland']
['Highest', 'Observation:', '27.8', 'ft', 'at', '10:00PM', 'Dec', '03,', '2019', 'McAlpine']
['Highest', 'Observation:', '27.8', 'ft', 'at', '11:00PM', 'Dec', '03,', '2019', 'McAlpine']
['Latest', 'observed', 'value:', '12.95', 'ft', 'at', '9:00', 'PM', 'EST', '4-Dec-2019.', 'Flood', 'Stage', 'is', '23', 'ft', 'Markland']
['Latest', 'observed', 'value:', '26.1', 'ft', 'at', '9:00', 'PM', 'EST', '4-Dec-2019.', 'Flood', 'Stage', 'is', '51', 'ft', 'McAlpine']
['Highest', 'Forecast:', '12.6', 'ft', '1:00AM', 'Dec', '05,', '2019', 'Markland']
['Highest', 'Forecast:', '25.7', 'ft', '1:00AM', 'Dec', '05,', '2019', 'McAlpine']
"""

""" This file contains code that can scrape the Nation Weather Service (NWS) website and read the 
river level data for both Markland and McAlpine dams. By using the mileage marker for Bushman's Lake 
the level of the river can be calculated.

McAlpine flood action levels: upper guage
Major Flood Stage: 	38
Moderate Flood Stage: 	30
Minor Flood Stage: 	23
First Action Stage: 	21

Markland flood action levels: lower guage
Major Flood Stage: 	74
Moderate Flood Stage: 	62
Flood Stage: 	51
Action Stage: 	49
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

# import arrow
from pprint import saferepr
from pprint import pprint
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

# import xml.etree.ElementTree as ET
from lxml import etree as ET


RUNTIME_NAME = path.basename(__file__)
Data_datestamp = datetime.now()

MCALPINE_DAM_URL = "https://water.weather.gov/ahps2/hydrograph.php?wfo=iln&gage=mklk2"
MCALPINE_DAM_NAME = 'McAlpine'
MCALPINE_DAM_DETAILS = [606.8, 407.18, 21, 23, 30, 38] #milemarker, guage elevation, first-action, minor, moderate, major-flood
MARKLAND_DAM_URL = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=142935&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=hydrograph"
MARKLAND_DAM_NAME = 'Markland'
MARKLAND_DAM_DETAILS = [531, 408, 49, 51, 62, 74]
RIVER_DETAILS = {
    MCALPINE_DAM_NAME: [MCALPINE_DAM_URL, MCALPINE_DAM_DETAILS],
    MARKLAND_DAM_NAME: [MARKLAND_DAM_URL, MARKLAND_DAM_DETAILS],
}
RIVERS = list(RIVER_DETAILS.keys())


@logger.catch
def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error("Error during requests to {0} : {1}".format(url, str(e)))
        return None


@logger.catch
def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.
    """
    content_type = resp.headers["Content-Type"].lower()
    return (
        resp.status_code == 200
        and content_type is not None
        and content_type.find("html") > -1
    )


@logger.catch
def log_error(e):
    """
    It is always a good idea to log errors. 
    This function just prints them, but you can
    make it do anything.
    """
    print(e)


@logger.catch
def ISO_datestring(dt, cl):
    isodatestr = dt.isoformat()
    if (
        cl[4] == "12:00AM"
    ):  # reset time to 00:00:00 since it incorrectly gets set to 12:00:00
        """ fix the timecode """
        isodatestr = isodatestr[0:11] + "00:00:00"
    return isodatestr


@logger.catch
def get_prime_readings_list(
    fqdn
):  # TODO change this to a dict key using simplified river name
    prime_list = []
    raw_response = simple_get(fqdn)
    html = BeautifulSoup(raw_response, "html.parser")
    # print(html)
    print('...begin list of "map" objects...')
    map_raw = html.select("map")[0]  # grab first item named 'map'
    # print(map_raw)
    parser = ET.XMLParser(recover=True)
    tree = ET.fromstring(str(map_raw), parser=parser)
    root = tree.getroottree()
    root_map = root.getroot()
    # print(root_map)
    map_dict = {}
    for child in root_map:
        # print('root_map_child tag: ', child.tag)
        try:
            child_list = child.attrib[
                "alt"
            ].split()  # TODO append simplified river name to list
            child_list.append(RIVERS[0])
            print("=== root_map_child attrib: ", child_list)
            print(child.attrib["alt"])
            searchdate = search_dates(child.attrib["title"], languages=["en"])
            if type(searchdate) == list:
                child_date = searchdate[0][1]  # TODO append dt obj to child_list
                date_iso = ISO_datestring(
                    child_date, child_list
                )  # TODO append datestr to child_list
                print("search:", type(child_date), date_iso)
                if date_iso in map_dict:
                    print("duplicate key!")  # TODO raise dupkey error
                    print(child_list)

                else:
                    map_dict[
                        date_iso
                    ] = child_list  # TODO add simplified river name to dict key
            else:
                print("no date found")
            # print('find:',list(datefinder.find_dates(child.attrib['title'])))
            # date = dateparser.parse(child.attrib['title'],fuzzy=True)
            # print('parse:',date)
        except ValueError as e:
            print(e)
            print("no date")
        except KeyError:
            print("no title")
    # pprint(map_dict)
    # TODO build dictionary of items as opposed to discarding some and listing others thus allowing further processing based on item tags.
    # for i, e in enumerate(map_raw.findAll('area')):
    #   place 'e' in dict
    # return dict

    """
    itemsToRemove = ['<area', 'coords', 'href', 'shape', 'alt=', ]
    for i, e in enumerate(map_raw.findAll('area')):
        t = str(e)
        l = t.split()
        s = []
        for e1 in l:
            remove = False
            for e2 in itemsToRemove:
                if e2 in e1:
                    remove = True
            if not remove:
                s.append(e1)
        if s[0] == 'Observation:' or s[0] == 'Forecast:' or s[0] == 'observed':
            prime_list.append(s)
    return prime_list
    """


@logger.catch
def build_river_dict(d, fqdn):
    """ return a dict of river names containing a dict of river conditions
    """
    logger.info("get readings")
    results = get_prime_readings_list(fqdn)
    logger.info("traverse results")
    for i, lst in enumerate(results):
        # logger.error(str(lst) + saferepr(i))
        d2 = {}
        for indx, item in enumerate(lst):
            d2[indx] = item
        d[i] = d2
    return d


@logger.catch
def defineLoggers():
    logger.add(
        sys.stderr,
        colorize=True,
        format="<green>{time}</green> {level} <red>{message}</red>",
        level=LOGGING_LEVEL,
    )
    logger.add(  # create a new log file for each run of the program
        RUNTIME_NAME + "_{time}.log", level="DEBUG"  # always send debug output to file
    )
    return


@logger.catch
def MAIN():
    results = "Blank"
    defineLoggers()
    logger.info("Program Start.", RUNTIME_NAME)
    results = get_prime_readings_list(MCALPINE_DAM_URL)
    # logger.info(saferepr(results))
    newdict = {}
    # dctnry = build_river_dict(newdict, MCALPINE_DAM_URL)
    # logger.info(saferepr(dctnry))
    return True


if __name__ == "__main__":
    MAIN()

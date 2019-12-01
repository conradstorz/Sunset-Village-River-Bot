""" This file contains code that can scrape the Nation Weather Service (NWS) website and read the 
river level data for both Markland and McAlpine dams. By using the mileage marker for Bushman's Lake 
the level of the river can be calculated.

McAlpine flood action levels
Major Flood Stage: 	38
Moderate Flood Stage: 	30
Flood Stage: 	23
Action Stage: 	21
"""
from loguru import logger
logger.remove() # stop any default logger
LOGGING_LEVEL = "DEBUG"
from os import sys, path
from datetime import datetime, timezone
from pprint import saferepr
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

RUNTIME_NAME = path.basename(__file__)
Data_datestamp = datetime.now()
MARKLAND_DAM_URL = 'https://water.weather.gov/ahps2/hydrograph.php?wfo=iln&gage=mklk2'
MCALPINE_DAM_URL = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=142935&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=hydrograph"


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
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None

@logger.catch
def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200 
            and content_type is not None 
            and content_type.find('html') > -1)

@logger.catch
def log_error(e):
    """
    It is always a good idea to log errors. 
    This function just prints them, but you can
    make it do anything.
    """
    print(e)


@logger.catch
def get_prime_readings_list(fqdn):
    prime_list = []
    raw_response = simple_get(MARKLAND_DAM_URL)
    html = BeautifulSoup(raw_response, 'html.parser')
    #print(html)
    print('...begin list of "map" objects...')
    map_raw = html.select('map')[0]
    #print(map_raw)
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

@logger.catch
def build_river_dict(dict, fqdn):
    """ return a dict of river names containing a dict of river conditions
    """
    d = {}
    results = get_prime_readings_list(fqdn)
    for r, i in enumerate(results):
        for item, indx in enumerate(r):
            d[i] = {indx: item}
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
        RUNTIME_NAME + "_{time}.log", level="DEBUG"  # always send debug output to file
    )
    return

@logger.catch
def MAIN():
    results = "Blank"
    defineLoggers()
    logger.info("Program Start.", RUNTIME_NAME)
    results = get_prime_readings_list(MCALPINE_DAM_URL)
    logger.info(saferepr(results))
    return True


if __name__ == "__main__":
    MAIN()
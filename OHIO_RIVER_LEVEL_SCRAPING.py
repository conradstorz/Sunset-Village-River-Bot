#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""NWS website scraping for river guage observations and forecasts.
This module will create local csv database of readings and forecasts.
Also the raw_data from scraping the NWS is saved to a text file for later examination.
Two datetimes are recorded. ScrapeTime and ForecastTime/ObservationTime.
Data is tuple of level and flowrate. (currently no flow data is published)
This program should be run daily (by cron for example).
A seperate program runs to analyze data and tweet when there is info to share.
If tweeting reports rising water then additional runs of scraping routine can be triggered.
"""
# import standard library modules
from logging import error
from time import sleep

# import custom modules
from pathlib import Path
from bs4 import BeautifulSoup, Comment
import datetime
import pytz
from tqdm import tqdm
from dateparser.search import search_dates
from loguru import logger
# Logging Setup
logger.remove()  # removes the default console logger provided by Loguru.
# I find it to be too noisy with details more appropriate for file logging.
# INFO and messages of higher priority only shown on the console.
logger.add(lambda msg: tqdm.write(msg, end=""), format="{message}", level="ERROR")
# This creates a logging sink and handler that puts all messages at or above the TRACE level into a logfile for each run.
logger.add(
    "./LOGS/file_{time}.log", level="TRACE", encoding="utf8"
)  # Unicode instructions needed to avoid file write errors.

# this section imports code from the pypi repository (CFSIV-utils-Conradical) of my own utilities.
import cfsiv_utils.WebScraping as ws
import cfsiv_utils.filehandling as fh
import cfsiv_utils.time_strings as ts

# These are the USGS identification numbers for river monitoring guages on the OHIO River
RIVER_GUAGE_IDS = [
    141893,
    143063,
    144287,
    142160,
    145137,
    143614,
    141268,
    144395,
    143843,
    142481,
    143607,
    145086,
    142497,
    151795,
    152657,
    141266,
    145247,
    143025,
    142896,
    144670,
    145264,
    144035,
    143875,
    143847,
    142264,
    152144,
    143602,
    144126,
    146318,
    141608,
    144451,
    144523,
    144877,
    151578,
    142935,
    142195,
    146116,
    143151,
    142437,
    142855,
    142537,
    142598,
    152963,
    143203,
    143868,
    144676,
    143954,
    143995,
    143371,
    153521,
    153530,
    143683,
]

USGS_WEBSITE_HEAD_URL = 'https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt[]='
USGS_WEBSITE_TAIL_URL = '&allpoints=150960&data[]=obs&data[]=xml'

# build urls...
USGS_URLS = []
for site in RIVER_GUAGE_IDS:
    USGS_URLS.append(f'{USGS_WEBSITE_HEAD_URL}{site}{USGS_WEBSITE_TAIL_URL}')

# TODO need guage location and relative elevation data dictionary

# TODO visualize data from guages to illustrate how a 'hump' of water moves down the river.
# possibly by graphing the guages as a flat surface and the water elevation above that imagined flat river.

# TODO predict the time of arrival of the 'hump' at various points. (machine learning?)

OUTPUT_ROOT = "CSV_DATA/"



@logger.catch
def extract_date(text_list):
    date_list = ts.extract_date(text_list)
    for date in date_list:
        if date != None:
            return date
    logger.debug(f'No parseable date found in: {text_list}')
    logger.warning('No parseable date found.')
    return ts.UTC_NOW()



@logger.catch
def pull_details(soup):
    """return specific parts of the scrape.

    Args:
        soup (bs4.BeautifulSoup): NWS guage scrape
    """
    guage_id = soup.h1["id"]
    guage_string = soup.h1.string
    # find the comments.
    comments = soup.findAll(text=lambda text: isinstance(text, Comment))
    # convert the findAll.ResultSet into a plain list.
    c_list = [c for c in comments]
    # Search the comments for a date of this scrape.
    # (the NWS webscrape contains exactly 1 date/timestamp found inside of a comment).
    scrape_date = extract_date(c_list)
    logger.info(f"Scrape date: {scrape_date}")
    nws_class = soup.find(class_="obs_fores")
    nws_obsfores_contents = nws_class.contents
    return (nws_obsfores_contents, guage_id, guage_string, scrape_date)


@logger.catch
def get_NWS_web_data(site, cache=False):
    """Return a BeautifulSoup (BS4) object from the Nation Weater Service (NWS)
    along with the ID# and TEXT describing the guage data.
    If CACHE then place the cleaned HTML into local storage for later processing by other code.
    """
    clean_soup = ws.retrieve_cleaned_html(site, cache)
    return pull_details(clean_soup)



@logger.catch
def FixDate(s, scrape_date, time_zone="UTC"):
    """Split date from time timestamp provided by NWS and add timezone label as well as correct year.
    Unfortunately, NWS chose not to include the year in their observation/forecast data.
    This will be problematic when forecast dates are into the next year.
    If Observation dates are in December, Forecast dates must be checked and fixed for roll over into next year.
    # NOTE: forecast dates will appear to be in the past as compared to the scrapping date if they are actually supposed to be next year.
    """
    # TODO make more robust string spliting
    date_string, time_string = s.split()
    hours, minutes = time_string.split(":")
    timestamp = datetime.time(int(hours), int(minutes))
    month_digits, day_digits = date_string.split("/")
    if len(month_digits) + len(day_digits) != 4:
        raise AssertionError("Month or Day string not correctly extracted.")
    corrected_year = ts.apply_logical_year_value_to_monthday_pair(date_string, scrape_date)
    # now place the timestamp back into the date object.
    corrected_datetime = datetime.datetime.combine(corrected_year, timestamp)
    return corrected_datetime.replace(tzinfo=pytz.UTC)



@logger.catch
def sort_and_label_data(web_data, guage_id, guage_string, scrape_date):
    readings = []
    labels = ["datetime", "level", "flow"]
    for i, item in enumerate(web_data):
        if i >= 1:  # zeroth item is an empty list
            # locate the name of this section (observed / forecast)
            section = item.find(class_="data_name").contents[0]
            sect_name = section.split()[0]
            row_dict = {"guage": guage_id, "type": sect_name}
            # extract all readings from this section
            section_data_list = item.find_all(class_="names_infos")
            # organize the readings and add details
            for i, data in enumerate(section_data_list):
                element = data.contents[0]
                pointer = i % 3  # each reading contains 3 unique data points
                if pointer == 0:  # this is the element for date/time
                    date = FixDate(element, scrape_date)
                    element = ts.timefstring(date)
                row_dict[labels[pointer]] = element 
                if pointer == 2:  # end of this reading
                    readings.append(row_dict)  # add to the compilation
                    # reset the dict for next reading
                    row_dict = {"guage": guage_id, "type": sect_name}
    return readings



@logger.catch
def Main():
    # for point in POINTS_OF_INTEREST:
    for point in USGS_URLS:
        logger.debug(f'Scraping point: {point}')
        time_now_string = ts.UTC_NOW_STRING()
        raw_data, guage_id, friendly_name, scrape_date = get_NWS_web_data(point, cache=True)
        # TODO verify webscraping success
        # DONE, store raw_data for ability to work on dates problem over the newyear transition.
        # It will be helpfull to have 12/28 to  January 4 scrapes for repeated test processing.
        # NOTE: cache=True above is used to make a local copy in the CWD of the original HTML scrape.
        data_list = sort_and_label_data(raw_data, guage_id, friendly_name, scrape_date)
        # TODO verify successful conversion of data
        for item in tqdm(data_list, desc=friendly_name):
            logger.debug(item)
            date, time = time_now_string.split("_")  # split date from time
            yy, mm, dd = date.split("-")
            OP = f"{yy}/{mm}/{dd}/"
            OD = f"{OUTPUT_ROOT}{OP}"
            FN = f"{time_now_string}"
            fh.write_csv([item], filename=FN, directory=OD)
        sleep(1)  # guarantee next point of interest gets a new timestamp.
        # some scrapes process in under 1 second and result in data collision.
        logger.info(time_now_string)
    return True


@logger.catch
def display_cached_data(number_of_scrapes):
    """process html collected previously and output to console.

    Args:
        number_of_scrapes (int) : number of scrapes to process from newest towards oldest
    """
    root = Path(Path.cwd(), "raw_web_scrapes")
    files = list(root.glob("*.rawhtml"))  # returns files ending with '.rawhtml'
    # sort the list oldest to newest
    files.sort(key=lambda fn: fn.stat().st_mtime, reverse=True)
    # recover the scrapes
    sample = []
    for i in range(number_of_scrapes):
        sample.append(files[i])

    data_sample = []
    for fl in sample:
        data_list = []
        with open(fl, "r") as txtfile:
            raw_html = txtfile.read()
        soup = BeautifulSoup(raw_html, "html.parser")
        raw_data, guage_id, friendly_name, scrape_date = pull_details(soup)
        data_list = sort_and_label_data(raw_data, guage_id, friendly_name, scrape_date)
        data_list = data_list[::-1]
        for i in range(9):
            data_sample.append(data_list[i])

    for point in data_sample[::-1]:
        datestamp = point["datetime"]
        if type(datestamp) == str:
            full_date = datestamp[:10]
        else:
            full_date = datestamp.strftime("%Y/%m/%d")

        _dummy = ts.apply_logical_year_value_to_monthday_pair(full_date, scrape_date)
        logger.info(f"Correct observation date: {_dummy}, original full date: {full_date}")
    # scrapetime = from filename
    return


if __name__ == "__main__":
    while True:
        Main()
        print("Sleeping...")
        total_sleep = 60 * 60 * 6
        for s in range(total_sleep):
            sleep(1)
            print(f"\r {total_sleep - s}         ", end="", flush=True)

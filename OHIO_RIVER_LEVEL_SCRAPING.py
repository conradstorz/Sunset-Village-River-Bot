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

# import custom modules
from pathlib import Path
from bs4 import BeautifulSoup, Comment
import datetime
import pytz
from dateutil.parser import parse, ParserError
from dateparser.search import search_dates
from loguru import logger
from data2csv import write_csv
from time_strings import UTC_NOW_STRING, apply_logical_year_value_to_monthday_pair, timefstring
from WebScraping import retrieve_cleaned_html
from filehandling import create_timestamp_subdirectory_Structure

# import standard library modules
from time import sleep


# TODO need guage location and elevation data
mcalpine_upper = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=142935&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=obs&data%5B%5D=xml"
mrklnd_lower = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=144523&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=obs&data%5B%5D=xml"
clifty_creek = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=144877&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=obs&data%5B%5D=xml"
lsvl_watertower = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=151578&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=obs&data%5B%5D=xml"
cincy = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt[]=144451&allpoints=150960&data[]=obs&data[]=xml"


POINTS_OF_INTEREST = [mcalpine_upper, mrklnd_lower, clifty_creek, lsvl_watertower, cincy]
# TODO visualize data from guages to illustrate how a 'hump' of water moves down the river.
# possibly by graphing the guages as a flat surface and the water elevation above that imagined flat river.
# TODO predict the time of arrival of the 'hump' at various points. (machine learning?)

OUTPUT_ROOT = "CSV_DATA/"


@logger.catch
def extract_date(text_list):
    """Searches a text string for a date reference and returns a datetime object.

    Args:
        text_list (list): A list of any length of strings of any length.

    Raises:
        TypeError: Input must be string
        ParseError: No decipherable date found.

    Returns:
        datetime.datetime: Datetime Object
    """
    if type(text_list) != list:
        raise TypeError('Argument must be a list.')

    for t in text_list:
        found = search_dates(t)
        if found != None:
            for itm in found:
                s, d = itm
                if len(s) == 8 and s[2] == ':' == s[5]:
                    return d
    raise ParserError('No parseable date found.')


@logger.catch
def pull_details(soup):
    """return specific parts of the scrape.

    Args:
        soup (bs4.BeautifulSoup): NWS guage scrape
    """
    guage_id = soup.h1["id"]
    guage_string = soup.h1.string
    # find the comments.
    comments = soup.findAll(text=lambda text:isinstance(text, Comment))
    # convert the findAll.ResultSet into a plain list.
    c_list = [c for c in comments]
    # Search the comments for a date (the NWS webscrape contains exactly 1 date/timestamp).
    scrape_date = extract_date(c_list)
    print(f'Scrape date: {scrape_date}')
    nws_class = soup.find(class_="obs_fores")
    nws_obsfores_contents = nws_class.contents
    return (nws_obsfores_contents, guage_id, guage_string, scrape_date)   

@logger.catch
def get_NWS_web_data(site, cache=False):
    """Return a BeautifulSoup (BS4) object from the Nation Weater Service (NWS)
    along with the ID# and TEXT describing the guage data.
    If CACHE then place the cleaned HTML into local storage for later processing by other code.
    """
    clean_soup = retrieve_cleaned_html(site, cache)
    content, id, name, date = pull_details(clean_soup)
    return (content, id, name, date)

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
    if len(month_digits)+len(day_digits) != 4:
        raise AssertionError('Month or Day string not correctly extracted.')

    corrected_year = apply_logical_year_value_to_monthday_pair(date_string, scrape_date)
    
    # now place the timestamp back into the date object.
    corrected_datetime = datetime.datetime.combine(corrected_year, timestamp)

    return corrected_datetime.replace(tzinfo=pytz.UTC)


@logger.catch
def sort_and_label_data(web_data, guage_id, guage_string, scrape_date):
    # TODO retrieve date of scrape from inside web_data.
    # The date of the webscrape is only included in one place inside
    # the original scrape.
    readings = []
    # Retrieve scrape year so that we can supply it to the processing of the date codes.
    yyyy = scrape_date.strftime("%Y") # NWS website operates on UTC
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
                    element = timefstring(date)
                row_dict[labels[pointer]] = element # TODO Add sanity check for this value being a string not an object.
                if pointer == 2:  # end of this reading
                    readings.append(row_dict)  # add to the compilation
                    # reset the dict for next reading
                    row_dict = {"guage": guage_id, "type": sect_name}
    return readings

@logger.catch
def compact_datestring(ds):
    """Return a string representing datetime of provided tuple."""
    return f"{ds[0]}{ds[1]}{ds[2]}_{ds[3]}{ds[4]}"

@logger.catch
def expand_datestring(ds):
    """Return elements of provided datestring."""
    x = ds.split("_")
    m = x[0][:2]
    d = x[0][2:4]
    y = x[0][-4:]
    t = x[1][:5]
    z = x[1][-3:]
    return (m, d, y, t, z)

@logger.catch
def Main():
    for point in POINTS_OF_INTEREST:
        time_now_string = UTC_NOW_STRING()
        raw_data, guage_id, friendly_name, scrape_date = get_NWS_web_data(point, cache=True)
        # TODO verify webscraping success
        # DONE, store raw_data for ability to work on dates problem over the newyear transition.
        # It will be helpfull to have 12/28 to  January 4 scrapes for repeated test processing.
        # NOTE: cache=True above is used to make a local copy in the CWD of the original HTML scrape.
        data_list = sort_and_label_data(raw_data, guage_id, friendly_name, scrape_date)
        # TODO verify successful conversion of data
        for item in data_list:
            print(item)
            output_directory = create_timestamp_subdirectory_Structure(time_now_string)
            OD = f"{OUTPUT_ROOT}{output_directory}"
            FN = f"{time_now_string}"
            write_csv([item], filename=FN, directory=OD)
        sleep(1) # guarnatee next point of interest gets a new timestamp.
        # some scrapes process in under 1 second and result in data collision.
        print(time_now_string)
    return True

@logger.catch
def display_cached_data(number_of_scrapes):
    """process html collected previously and output to console.

    Args:
        number_of_scrapes (int) : number of scrapes to process from newest towards oldest
    """
    root = Path(Path.cwd(), 'raw_web_scrapes')
    files = list(root.glob('*.rawhtml')) # returns files ending with '.rawhtml'
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
        datestamp = point['datetime']
        if type(datestamp) == str:
            full_date = datestamp[:10]
        else:
            full_date = datestamp.strftime("%Y/%m/%d")

        _dummy = apply_logical_year_value_to_monthday_pair(full_date, scrape_date)
        print(f'Correct observation date: {_dummy}, original full date: {full_date}')
    # scrapetime = from filename
    return



if __name__ == "__main__":
    while True:
        Main()
        print('Sleeping...')
        total_sleep = 60*60*6
        for s in range(total_sleep):
            sleep(1)
            print(f"\r {total_sleep - s}         ", end="", flush=True)

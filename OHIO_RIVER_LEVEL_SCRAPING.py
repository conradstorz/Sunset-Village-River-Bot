#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""NWS website scraping for river guage observations and forecasts.
This module will create local csv database of readings and forecasts.
Two datetimes are recorded. ScrapeTime and ForecastTime/ObservationTime.
Data is tuple of level and flowrate. (currently no flow data is published)
"""
# TODO place these readings into a csv file for later processing.
# TODO name csv files based on datetime of scrape

from WebScraping import retrieve_cleaned_html
from time_strings import UTC_NOW_STRING
from filehandling import create_timestamp_subdirectory_Structure
from data2csv import write_csv

mcalpine = 'https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=142935&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=obs&data%5B%5D=xml'
# TODO add more points of interest
mrklnd = 'https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=144523&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=obs'

POINTS_OF_INTEREST = [mcalpine, mrklnd]
OUTPUT_ROOT = 'CSV_DATA/'

def get_NWS_web_data(site):
    clean_soup = retrieve_cleaned_html(site)
    guage_id = clean_soup.h1['id']
    guage_string = clean_soup.h1.string
    nws_class = clean_soup.find(class_ = 'obs_fores')
    nws_obsfores_contents = nws_class.contents
    return (nws_obsfores_contents, guage_id, guage_string)


def FixDate(s, currentyear, time_zone = 'UTC'):
    """Split date from time and add timezone label.
    Unfortunately, NWS chose not to include the year. 
    This will be problematic when forecast dates are into the next year.
    If Observation dates are in December, Forecast dates must be checked and fixed for roll over into next year.
    """
    date_string, time_string = s.split()
    month_digits, day_digits = date_string.split('/')
    return f"{currentyear}-{month_digits}-{day_digits}_{time_string}{time_zone}"
    

def sort_and_label_data(web_data, guage_id, guage_string):
    readings = []
    labels = ['datetime', 'level', 'flow']
    for i, item in enumerate(web_data):
        if i >= 1: # zeroth item is an empty list
            # locate the name of this section (observed / forecast)
            section = item.find(class_ = 'data_name').contents[0]
            sect_name = section.split()[0]
            row_dict = {'guage': guage_id, 'type': sect_name}
            # extract all readings from this section
            section_data_list = item.find_all(class_ = 'names_infos')
            # organize the readings and add details
            for i, data in enumerate(section_data_list):
                element = data.contents[0]
                pointer = i % 3 # each reading contains 3 unique data points
                if pointer == 0: # this is the element for date/time
                    element = FixDate(element, '2020')
                row_dict[labels[pointer]] = element
                if pointer == 2: # end of this reading
                    readings.append(row_dict) # add to the compilation
                    # reset the dict for next reading
                    row_dict = {'guage': guage_id, 'type': sect_name}
    return readings


def compact_datestring(ds):
    """Return a string representing datetime of provided tuple.
    """
    return f'{ds[0]}{ds[1]}{ds[2]}_{ds[3]}{ds[4]}'


def expand_datestring(ds):
    """Return elements of provided datestring.
    """
    x = ds.split('_')
    m = x[0][:2]
    d = x[0][2:4]
    y = x[0][-4:]
    t = x[1][:5]
    z = x[1][-3:]
    return (m, d, y, t, z)


def Main():
    for point in POINTS_OF_INTEREST:
        time_now_string = UTC_NOW_STRING()
        raw_data, guage_id, friendly_name = get_NWS_web_data(point)
        # TODO verify webscraping success
        data_list = sort_and_label_data(raw_data, guage_id, friendly_name)
        # TODO verify successful conversion of data
        for item in data_list:
            print(item)
            # TODO place item in csv file
            output_directory = create_timestamp_subdirectory_Structure(time_now_string)
            OD = f"{OUTPUT_ROOT}{output_directory}"
            FN = f"{time_now_string}"
            write_csv([item], filename=FN, directory=OD)

        print(time_now_string)
    return True


Main()
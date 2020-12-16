#!/usr/bin/env python
# -*- coding: utf-8 -*-
# version 2.0
"""Create a file and populate with items from a data structure.
    # TODO move this functionality into the filehandling module and standardize.
"""

import csv
from pathlib import Path
from filehandling import check_and_validate
from loguru import logger


@logger.catch
def write_csv(data, filename="temp.csv", directory="CSV_DATA", use_subs=False):
    """'data' is expected to be a list of dicts 
    Take data and write all fields to storage as csv with headers from keys.
    if filename already exists automatically append to end of file if headers match.

with open(r'names.csv', 'a', newline='') as csvfile:
    fieldnames = ['This','aNew']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writerow({'This':'is', 'aNew':'Row'})

    Process: file exist? headers match? append data.
    file exist? headers mis-match. raise exception
    no file? create file and save data.
    """
    # create csv file path
    dirobj = Path(Path.cwd(), directory)
    dirobj.mkdir(parents=True, exist_ok=True)    
    pathobj = check_and_validate(filename, dirobj)

    if not pathobj.exists():
        with open(pathobj, "w", newline="") as csvfile:
            csv_obj = csv.writer(csvfile, delimiter=",")
            headers = data[0].keys()
            csv_obj.writerow(headers)
    with open(pathobj, "a+", newline="") as csvfile:
        csv_obj = csv.writer(csvfile, delimiter=",")
        for item in data:  # data should be the list of dicts contaning observations/forecasts.
            csv_obj.writerow(item.values())

    return



if __name__ == "__main__":
    from pathlib import Path
    this_file = Path(__file__)
    print(f'This file {this_file} has no current standalone function.')

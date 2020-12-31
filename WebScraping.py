#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This file contains basic webscraping elements found in 
https://realpython.com/python-web-scraping-practical-introduction/
"""

from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

from loguru import logger
from pathlib import Path
from filehandling import check_and_validate
from time_strings import UTC_NOW_STRING


@logger.catch
def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise raise exception if bad response or RequestException
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                raise Warning(f'Bad response from: {url}')

    except RequestException as e:
        log_error(f"Error during requests to {url} : {str(e)}")
        raise Warning(f'{str(e)}')



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


def save_html_text(txt):
    """Place 'txt' in a subdirectory in the current working directory 
    under a filename based on the current time.
    This will be useful for additional review of accuracy in data extraction.
    """
    # create file path
    filename = f'{UTC_NOW_STRING()}_webscrape.rawhtml'
    # use a subdirectory of current working directory
    dirobj = Path(Path.cwd(), 'raw_web_scrapes')
    dirobj.mkdir(parents=True, exist_ok=True)   
    # ensure that filename only contains valid characters 
    pathobj = check_and_validate(filename, dirobj)
    with open(pathobj, "w") as txtfile:
        txtfile.write(str(txt))
    return None


@logger.catch
def retrieve_cleaned_html(url, cache=False):
    raw_resp = simple_get(url)
    if raw_resp is not None:
        if cache:
            save_html_text(raw_resp)
        return BeautifulSoup(raw_resp, "html.parser")
    return None

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
def retrieve_cleaned_html(url):
    raw_resp = simple_get(url)
    if raw_resp is not None:
        # print(BeautifulSoup(raw_resp, "xml").prettify())
        return BeautifulSoup(raw_resp, "html.parser")
    return None

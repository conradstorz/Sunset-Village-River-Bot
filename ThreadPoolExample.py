import time
import concurrent.futures
import urllib.request
from OHIO_RIVER_LEVEL_SCRAPING import USGS_URLS as URLS

"""URLS = ['http://www.foxnews.com/',
        'http://www.cnn.com/',
        'http://europe.wsj.com/',
        'http://www.bbc.co.uk/',
        'http://some-made-up-domain.com/']
"""

# Retrieve a single page and report the URL and contents
def load_url(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as conn:
        return conn.read()


def use_no_threads(urls_list):
    """retrieve the urls one at a time"""
    for url in urls_list:
        try:
            data = load_url(url, 60)
        except Exception as exc:
            print('%r generated an exception: %s' % (url, exc))
        else:
            print('%r page is %d bytes' % (url, len(data)))



def use_threadpools(urls_list):
    """retrieve the urls concurrently"""
    # We can use a with statement to ensure threads are cleaned up promptly
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(load_url, url, 60): url for url in urls_list}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
            else:
                print('%r page is %d bytes' % (url, len(data)))

start = time.time()
print(start)
use_no_threads(URLS)
timeofnothreads = time.time()
print(timeofnothreads)
use_threadpools(URLS)
endofthreadpool = time.time()
print(endofthreadpool)
print()
print(f'Time to completion: {timeofnothreads - start:.1f} without threads and {endofthreadpool - timeofnothreads:.1f} with threads.')

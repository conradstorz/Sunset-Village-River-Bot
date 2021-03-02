import sys
from loguru import logger
from OHIO_RIVER_LEVEL_SCRAPING import display_cached_data

logger.add(sys.stderr, format="{time} {level} {message}", filter="my_module", level="DEBUG")
logger.info('Start')
display_cached_data(9)
logger.info('End')

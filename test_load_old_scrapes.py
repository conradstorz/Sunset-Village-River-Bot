import sys
from loguru import logger
from OHIO_RIVER_LEVEL_SCRAPING import display_cached_data

logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="INFO")
logger.info('Start')
display_cached_data(99)
logger.info('End')

import sys
from loguru import logger
from OHIO_RIVER_LEVEL_SCRAPING import display_cached_forecast_data2 as do

logger.remove()
logger.add(sys.stdout, format="{time} {level} {message}", level="DEBUG")
logger.info('Start')
do(6)
logger.info('End')

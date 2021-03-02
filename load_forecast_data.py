import sys
from loguru import logger
from OHIO_RIVER_LEVEL_SCRAPING import display_cached_forecast_data2 as sample

logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
logger.info('Start')
sample(1)
logger.info('End')

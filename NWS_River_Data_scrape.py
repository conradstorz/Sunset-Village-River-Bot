""" This file contains code that can scrape the Nation Weather Service (NWS) website and read the 
river level data for both Markland and McAlpine dams. By using the mileage marker for Bushman's Lake 
the level of the river can be calculated. 
"""
from loguru import logger

logger.remove()  # stop any default logger
LOGGING_LEVEL = "DEBUG"
from os import sys, path
from datetime import datetime, timezone
from pprint import saferepr
import requests
from bs4 import BeautifulSoup as BS

runtime_name = path.basename(__file__)
Data_datestamp = datetime.now()
Data_datestamp = Data_datestamp.strftime("%m/%d/%Y, %H:%M")

ALERT_LEVELS = ["major", "moderate", "flood", "action", "low"]

SABINE_RIVER_URL = "http://water.weather.gov/ahps2/river.php?wfo=SHV&wfoid=18715&riverid=203413&pt%5B%5D=all&allpoints=143204%2C147710%2C141425%2C144668%2C141750%2C141658%2C141942%2C143491%2C144810%2C143165%2C145368&data%5B%5D=xml"

OHIO_RIVER_URL = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=all&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=all&data%5B%5D=xml"

MRKLND_2_MCALPN_RIVER_URL = "https://water.weather.gov//ahps2/river.php?wfo=lmk&wfoid=18699&riverid=204624&pt%5B%5D=144523&pt%5B%5D=142935&allpoints=150960%2C141893%2C143063%2C144287%2C142160%2C145137%2C143614%2C141268%2C144395%2C143843%2C142481%2C143607%2C145086%2C142497%2C151795%2C152657%2C141266%2C145247%2C143025%2C142896%2C144670%2C145264%2C144035%2C143875%2C143847%2C142264%2C152144%2C143602%2C144126%2C146318%2C141608%2C144451%2C144523%2C144877%2C151578%2C142935%2C142195%2C146116%2C143151%2C142437%2C142855%2C142537%2C142598%2C152963%2C143203%2C143868%2C144676%2C143954%2C143995%2C143371%2C153521%2C153530%2C143683&data%5B%5D=xml"

RIVER_GUAGE_NAMES = [
    "Ohio River At Markland Lower (MKLK2)",
    "Ohio River At McAlpine Upper (MLUK2)",
]

LOCATION_OF_INTEREST = 584  # river mile marker @ Bushman's Lake
LOCATION_OF_MARKLAND = 531
LOCATION_OF_MCALPINE = 604


@logger.catch
def Get_Data(data_url):
    Data_datestamp = datetime.now()
    Data_datestamp = Data_datestamp.strftime("%m/%d/%Y, %H:%M")
    logger.info("Retrieve Data from website.")
    headers = {
        "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0"
    }
    response = requests.get(data_url, headers=headers)
    logger.debug(response.text)
    # TODO check for valid response
    decoded = BS(response.text, "lxml")
    logger.debug(decoded)
    return (decoded, Data_datestamp)


@logger.catch
def Process_Data():
    logger.info("Place Data into a list of dictionaries.")
    soup, time = Get_Data(MRKLND_2_MCALPN_RIVER_URL)

    data = []
    # process the data returned from waterdata.usgs.gov
    # into a list of dictionaries
    for river in soup.select("h1.data_name"):
        logger.debug("RIVER: " + river.get_text())
        river_name = river.get_text(strip=True)
        logger.debug("RIVER NAME: " + river_name)
        river_data = river.find_next_sibling("div")
        logger.debug("RIVER DATA: " + river_data.get_text())
        logger.debug(
            "RIVER DATA: " + river_data.select_one(".stage_stage_flow").get_text()
        )
        logger.debug(
            "RIVER DATA: " + river_data.select_one(".flood_stage_flow").get_text()
        )
        logger.debug(
            "RIVER DATA: "
            + river_data.select_one(
                ".current_warns_statmnts_ads > b"
            ).next_sibling.strip()
        )
        # logger.debug('RIVER DATA: '+ river_data)
        data.append(
            {
                "name": river_name,
                "stage": river_data.select_one(".stage_stage_flow")
                .get_text(strip=True)
                .replace("Latest Stage: ", ""),
                "flood_lvl": river_data.select_one(".flood_stage_flow")
                .get_text(strip=True)
                .replace("Flood Stage: ", "")
                .replace(" Feet", ""),
                "warns": river_data.select_one(
                    ".current_warns_statmnts_ads > b"
                ).next_sibling.strip(),
                "alerts": {
                    alert_name: alert_value.get_text(strip=True)
                    for alert_name, alert_value in zip(
                        ALERT_LEVELS,
                        river_data.select(
                            ".flood_his_lwr .box_square table tr > td:nth-of-type(2)"
                        ),
                    )
                },
            }
        )

    return (data, time)


@logger.catch
def pull_river_levels(data, GUAGE_NAMES):
    logger.info("Create dict with float value keyed by river guage.")
    levels = {}
    for guage_dict in data:
        if "name" in guage_dict:
            txt_str = guage_dict["name"]
            if txt_str in GUAGE_NAMES:
                stage_txt = guage_dict["stage"]
                levels[txt_str] = float(stage_txt)
    return levels


@logger.catch
def Calclate_level(data, offset):
    logger.info("Calculate probable river level at point of interest.")
    up_river_guage = data[RIVER_GUAGE_NAMES[0]]
    down_river_guage = data[RIVER_GUAGE_NAMES[1]]
    slope = up_river_guage - down_river_guage
    per_mile_slope = slope / (LOCATION_OF_MCALPINE - LOCATION_OF_MARKLAND)
    projection = (
        LOCATION_OF_MCALPINE - LOCATION_OF_INTEREST
    ) * per_mile_slope + down_river_guage
    return projection


@logger.catch
def calculated_Bushmans_river_level():
    river_data, timestamp = Process_Data()
    logger.debug(saferepr(river_data))
    output = [str(timestamp)]
    river_levels = pull_river_levels(river_data, RIVER_GUAGE_NAMES)
    logger.info(saferepr(river_levels))
    output.append("River Levels: " + saferepr(river_levels))

    projected_level_at_Bushmans = Calclate_level(river_levels, LOCATION_OF_INTEREST)
    # print("projected_level_at_Bushmans ", projected_level_at_Bushmans)
    output.append("calculated_level_at_Bushmans " + saferepr(projected_level_at_Bushmans))

    return output


@logger.catch
def defineLoggers():
    logger.add(
        sys.stderr,
        colorize=True,
        format="<green>{time}</green> {level} <red>{message}</red>",
        level=LOGGING_LEVEL,
    )
    logger.add(  # create a new log file for each run of the program
        runtime_name + "_{time}.log", level="DEBUG"  # always send debug output to file
    )
    return


@logger.catch
def MAIN():
    results = "Blank"
    defineLoggers()
    logger.info("Program Start.")
    results = calculated_Bushmans_river_level()
    print(saferepr(results))
    return True


if __name__ == "__main__":
    MAIN()

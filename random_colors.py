#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" expose methods of setting random colors on the RaspberryPi SenseHat display.
Depends on a JSON file declaring color names and RGB values.
"""

from itertools import product
from random import choice, shuffle
from time import sleep
import json
from sense_hat import SenseHat


with open("rgb_color_codes.json", "r") as read_file:
    color_dict = json.load(read_file)

COLOR_KEYS = list(color_dict.keys())
index = list(range(8))


def Set_Random_Pixels(senseObj, x=index, y=index, pace=0.01, rounds=99):
    """ Fill display with random pixel colors.
    Params: senseObj = senseHat Object pointer (required)
    Optional: ,x,y list of index values [valid=0-7 and 1 to 8 values] (size of area to display)
    Optional: ,pace >0<=1 (speed of change)
    Optional: ,rounds >=1 (number of times each pixel will change on average)
    """
    # TODO range check x,y, and pace
    # TODO type check senseObj
    field = [int(rounds) for i in range(len(x) * len(y))]
    while sum(field) > -(rounds*100): # extend run time 
        color = choice(COLOR_KEYS)
        pixel_x = choice(x)
        pixel_y = choice(y)
        iters = field[pixel_x * 8 + pixel_y]
        field[pixel_x * 8 + pixel_y] = iters - 1
        senseObj.set_pixel(pixel_x, pixel_y, color_dict[color]["rgb"])
        delay = (sum(field) / rounds) / (100 / pace)
        if delay > 0:
            sleep(delay)
        else:
            sleep(.0001)
    return color


def random_to_solid(senseObj, colorName="black", x=index, y=index, fast=False):
    if colorName not in color_dict.keys():
        raise ValueError
    # TODO range check x,y
    if fast == True:
        field = list(range(len(x) * len(y)))
        shuffle(field)  # scramble list
        while len(field) > 0:
            pxl = field.pop()
            x = int(pxl / 8)
            y = int(pxl % 8)
            senseObj.set_pixel(x, y, color_dict[colorName]["rgb"])
            sleep(len(field)/2*.01)
    else:
        field = [1 for i in range(len(x) * len(y))]
        while sum(field) > 0:
            pixel_x = choice(x)
            pixel_y = choice(y)
            pxl = pixel_x * 8 + pixel_y
            if field[pxl] != 0:
                field[pxl] = 0
                senseObj.set_pixel(pixel_x, pixel_y, color_dict[colorName]["rgb"])
            sleep(0.1)
    return


def Main(sense):
    Set_Random_Pixels(sense)
    sense.low_light = True
    sense.clear(255, 255, 255)
    return


if __name__ == "__main__":
    sense = SenseHat()
    Main(sense)

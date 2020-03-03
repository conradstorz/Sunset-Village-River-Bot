#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" expose methods of setting random colors on the RaspberryPi SenseHat display.
Depends on a JSON file declaring color names and RGB values.
"""

from itertools import product
from random import choice
from time import sleep
import json
from sense_hat import SenseHat


with open("rgb_color_codes.json", "r") as read_file:
    color_dict = json.load(read_file)

COLOR_KEYS = list(color_dict.keys())


def Set_Random_Pixels(sense):
    """ Fill display with random pixel colors.
    """
    index = list(range(8))
    x = index
    y = index
    field = [1 for i in range(len(x)*len(y))]
    while sum(field) > 1:
        color = choice(COLOR_KEYS)
        pixel_x = choice(x)
        pixel_y = choice(y)
        field[pixel_x * 8 + pixel_y] = 0
        sense.set_pixel(pixel_x, pixel_y, color_dict[color]['rgb'])
    return


def Main(sense):
    Set_Random_Pixels(sense)
    sense.low_light = True
    sense.clear(255, 255, 255)
    return

if __name__ == "__main__":
    sense = SenseHat()
    Main(sense)

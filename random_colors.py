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
index = list(range(8))

def Set_Random_Pixels(senseObj, x = index, y = index, pace = .1, rounds = 50):
    """ Fill display with random pixel colors.
    """
    # TODO range check x,y, and pace
    # TODO type check senseObj
    field = [rounds for i in range(len(x)*len(y))]
    while sum(field) > 0:
        color = choice(COLOR_KEYS)
        pixel_x = choice(x)
        pixel_y = choice(y)
        iters = field[pixel_x * 8 + pixel_y]
        field[pixel_x * 8 + pixel_y] = iters - 1
        senseObj.set_pixel(pixel_x, pixel_y, color_dict[color]['rgb'])
        sleep((sum(field) / rounds)/(100 / pace))
    return


def Main(sense):
    Set_Random_Pixels(sense)
    sense.low_light = True
    sense.clear(255, 255, 255)
    return

if __name__ == "__main__":
    sense = SenseHat()
    Main(sense)

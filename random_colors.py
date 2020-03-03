from itertools import product
from random import choice
from time import sleep
import json
from sense_hat import SenseHat

index = list(range(8))
x = index
y = index

sense = SenseHat()
sense.low_light = True
sense.clear(255, 255, 255)

with open("rgb_color_codes.json", "r") as read_file:
    color_dict = json.load(read_file)

keys = list(color_dict.keys())

while True:
    color = choice(keys)
    pixel_x = choice(x)
    pixel_y = choice(y)

    #print(color)
    sense.set_pixel(pixel_x, pixel_y, color_dict[color]['rgb'])
    #sleep(.1)


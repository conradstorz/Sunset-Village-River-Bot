from itertools import product
from random import choice
from time import sleep
import json
from sense_hat import SenseHat

sense = SenseHat()

sense.clear(255, 255, 255)

with open("rgb_color_codes.json", "r") as read_file:
    color_dict = json.load(read_file)

keys = color_dict.keys()

while True:
    color = choice(keys)
    print(color)
    sense.clear(color_dict[color])
    sleep(1)


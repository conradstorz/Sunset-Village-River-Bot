from itertools import product
from random import choice
from time import sleep
import json
from sense_hat import SenseHat

sense = SenseHat()

sense.clear(255, 255, 255)

with open("data_file.json", "r") as read_file:
    color_dict = json.load(read_file)

while True:
    color = choice(color_dict.keys())
    print(color)
    sense.clear(color_dict[color])
    sleep(1)

    
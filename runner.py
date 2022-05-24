import pandas as pd
from scrub_main import scrub_experiment
from scrubber import Scrubber
import os


def get_attributes():
    my_row = 0
    runs_filepath = './profiles/alt-right/runs.csv'
    runs = pd.read_csv(runs_filepath).to_dict('index')
    attributes = runs[my_row]

    return attributes

def main():
    attributes = get_attributes()

    # Creating the outputs directory
    os.makedirs('outputs')
    os.makedirs('outputs/fails')

    bot = Scrubber(**attributes)

    scrub_experiment(bot)

if __name__ == '__main__':
    main()

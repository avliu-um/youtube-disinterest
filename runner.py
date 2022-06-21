import pandas as pd
from scrub_main import scrub_experiment

"""
Code to run the rows of the CSV's in the 'runs' folder
"""


def get_attributes(runs_filepath, row):
    runs = pd.read_csv(runs_filepath).to_dict('index')
    attributes = runs[row]

    return attributes


def main():
    runs_filepath = 'runs/strategy_test_runs.csv'
    my_row = 0

    attributes = get_attributes(runs_filepath, my_row)
    scrub_experiment(attributes)


if __name__ == '__main__':
    main()

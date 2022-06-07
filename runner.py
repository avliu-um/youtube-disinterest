import pandas as pd
from scrub_main import scrub_experiment


def get_attributes(runs_filepath, row):
    runs = pd.read_csv(runs_filepath).to_dict('index')
    attributes = runs[row]

    return attributes


def main():
    runs_filepath = 'runs/alt-right_runs.csv'
    my_row = 4

    attributes = get_attributes(runs_filepath, my_row)
    scrub_experiment(attributes)


if __name__ == '__main__':
    main()

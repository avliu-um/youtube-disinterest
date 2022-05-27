import pandas as pd
from scrub_main import scrub_experiment


def get_attributes():
    my_row = 0
    runs_filepath = 'runs/alt-right_runs.csv'
    runs = pd.read_csv(runs_filepath).to_dict('index')
    attributes = runs[my_row]

    return attributes


def main():
    attributes = get_attributes()
    scrub_experiment(attributes)


if __name__ == '__main__':
    main()

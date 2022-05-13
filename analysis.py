import pandas as pd

# Create the 'stain' column which is True if the video is in the list of channels
def stain_col(results_df, channels):
    results_df['stain'] = results_df.apply(
        lambda row: row['channel_id'] in channels,
        axis=1
    )

def stain_data(df):
    percents = df.groupby(['level'])['stain'].agg([percentage_true])
    return percents

# Find the percentage True values in a list
def percentage_true(values):
    num = 0
    for v in values:
        if v:
            num += 1
    return num * 1.0 / len(values)

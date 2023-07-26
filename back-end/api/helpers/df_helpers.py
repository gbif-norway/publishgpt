import numpy as np
import pandas as pd
from skimage.measure import label, regionprops

def trim_dataframe(df):
    # Replace empty spaces with NaN
    df.replace('', np.nan, inplace=True)

    # Get the bounds where the non-NaN values start and end
    rows = np.where(df.notna().any(axis=1))[0]
    cols = np.where(df.notna().any(axis=0))[0]

    trimmed_df = df.iloc[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]

    # If the first column is just a list of numbers from 0+ or 1+, it is meaningless, drop it
    first_column = trimmed_df.iloc[:, 0]
    if first_column.is_monotonic_increasing and first_column.min() in [0, 1] and np.all(np.diff(first_column) == 1):
        trimmed_df = trimmed_df.drop(trimmed_df.columns[0], axis=1)

    return trimmed_df.fillna('')

def extract_sub_tables_based_on_null_boundaries(df):
    larr = label(np.array(df.notnull()).astype("int"))
    dfs = []
    for s in regionprops(larr):
        sub_df = df.iloc[s.bbox[0]:s.bbox[2], s.bbox[1]:s.bbox[3]]
        dfs.append(sub_df)

    # Start from the second last dataframe and work up to the first
    for i in range(len(dfs) - 2, -1, -1):
        # If the dataframe has only 1 or 2 rows and the number of columns matches
        if len(dfs[i]) <= 2 and dfs[i].shape[1] == dfs[i + 1].shape[1]:
            # Append it to the dataframe below it
            dfs[i + 1] = pd.concat([dfs[i], dfs[i + 1]]).reset_index(drop=True)
            # Remove the merged dataframe from the list
            del dfs[i]
    
    return [df.reset_index(drop=True) for df in dfs]

def extract_sub_tables(df, min_rows=2):
    all_null_rows = df.isnull().all(axis=1)
    start = 0
    tables = []
    for i, is_null in enumerate(all_null_rows):
        if is_null:
            if i - start >= min_rows:
                tables.append(df.iloc[start:i])
            start = i + 1
    if len(df) - start >= min_rows:
        tables.append(df.iloc[start:])
    return [trim_dataframe(t) for t in tables]


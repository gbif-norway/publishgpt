import numpy as np

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


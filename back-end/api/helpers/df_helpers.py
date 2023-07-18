import numpy as np
import pandas as pd
from skimage.measure import label, regionprops
from api.models import DataFrame

def trim_dataframe(df):
    # Replace empty spaces with NaN
    df.replace('', np.nan, inplace=True)

    # Get the bounds where the non-NaN values start and end
    rows = np.where(df.notna().any(axis=1))[0]
    cols = np.where(df.notna().any(axis=0))[0]

    # Trim the DataFrame based on these bounds
    trimmed_df = df.iloc[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]

    # If the first column is just a list of numbers from 0+ or 1+, it is meaningless, drop it
    first_column = trimmed_df.iloc[:, 0]
    if first_column.is_monotonic_increasing and first_column.min() in [0, 1] and np.all(np.diff(first_column) == 1):
        trimmed_df = trimmed_df.drop(trimmed_df.columns[0], axis=1)

    return trimmed_df

def trunc_df_to_string(df, max_rows=5, max_columns=5):
    max_rows = max(max_rows, 5)    # At least 5 to show truncation correctly
    max_columns = max(max_columns, 5)    # At least 5 to show truncation correctly
    original_rows, original_cols = df.shape

    if len(df) > max_rows:
        top = df.head(max_rows // 2)
        bottom = df.tail(max_rows // 2)
        df = pd.concat([top, pd.DataFrame({col: ['...'] for col in df.columns}), bottom])

    if len(df.columns) > max_columns:
        df = df.iloc[:, :max_columns//2].join(pd.DataFrame({ '...': ['...']*len(df) })).join(df.iloc[:, -max_columns//2:])

    return df.to_string() + f"\n\n[{original_rows} rows x {original_cols} columns]"

def extract_sub_tables_based_on_null_boundaries(dataframe:DataFrame):
    df = dataframe.df
    larr = label(np.array(df.notnull()).astype("int"))
    dfs = []

    for s in regionprops(larr):
        sub_df = (df.iloc[s.bbox[0]:s.bbox[2], s.bbox[1]:s.bbox[3]]
                    .pipe(lambda df_: df_.rename(columns=df_.iloc[0])
                    .drop(df_.index[0])))
        dfs.append(sub_df)

    # Start from the second last dataframe and work up to the first
    for i in range(len(dfs) - 2, -1, -1):
        # If the dataframe has only 1 or 2 rows and the number of columns matches
        if len(dfs[i]) <= 2 and dfs[i].shape[1] == dfs[i + 1].shape[1]:
            # Append it to the dataframe below it
            dfs[i + 1] = pd.concat([dfs[i], dfs[i + 1]]).reset_index(drop=True)
            # Remove the merged dataframe from the list
            del dfs[i]
    
    for new_df in dfs:
        DataFrame.objects.create(
            dataset=dataframe.dataset,
            parent=dataframe.dataset,
            df = new_df
        )

    return dfs
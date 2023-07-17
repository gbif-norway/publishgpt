import pandas as pd
import json
import pandas as pd

def function_name_in_text(function_names, text):
    for string in function_names:
        if string in text:
            return True
    return False

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

def snapshot_data(df, char_limit=1000):
    top_rows = []
    bottom_rows = []

    # For top rows
    total_chars = 0
    for i, row in enumerate(df.iterrows()):
        row_string = json.dumps(row[1].to_dict())
        new_total_chars = total_chars + len(row_string)
        # Special case for the first row
        if i == 0 or new_total_chars <= char_limit:
            total_chars = new_total_chars
            top_rows.append(row[1])
        else:
            break

    # For bottom rows, we'll reverse the DataFrame
    total_chars = 0
    for i, row in enumerate(df.iloc[::-1].iterrows()):
        row_string = json.dumps(row[1].to_dict())
        new_total_chars = total_chars + len(row_string)
        # Special case for the first row
        if i == 0 or new_total_chars <= char_limit:
            total_chars = new_total_chars
            bottom_rows.append(row[1])
        else:
            break

    # Convert list of Series to DataFrame
    top_df = pd.DataFrame(top_rows)
    bottom_df = pd.DataFrame(bottom_rows[::-1]) # Revert the order back to original

    return top_df, bottom_df

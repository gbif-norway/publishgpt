import pandas as pd
import json


def snapshot_data(df, char_limit=1000):
    top_rows = []
    bottom_rows = []
    
    # For top rows
    total_chars = 0
    for _, row in df.iterrows():
        row_string = json.dumps(row.to_dict())
        if total_chars + len(row_string) > char_limit:
            break
        total_chars += len(row_string)
        top_rows.append(row)
    
    # For bottom rows, we'll reverse the DataFrame
    total_chars = 0
    for _, row in df.iloc[::-1].iterrows():
        row_string = json.dumps(row.to_dict())
        if total_chars + len(row_string) > char_limit:
            break
        total_chars += len(row_string)
        bottom_rows.append(row)
    
    # Convert list of Series to DataFrame
    top_df = pd.DataFrame(top_rows)
    bottom_df = pd.DataFrame(bottom_rows)
    
    return top_df, bottom_df

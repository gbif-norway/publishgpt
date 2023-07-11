import pandas as pd
from google.cloud import translate_v2 as translate
import langcodes


def merge_top_rows_into_header(df, number_of_top_rows_to_merge):
    # Merge the first x rows to create a new header
    header = df.iloc[:number_of_top_rows_to_merge].fillna('').apply(lambda x: '_'.join(x), axis=0)

    # Replace all leading/trailing underscores
    header = header.str.strip('_')

    # Drop the rows that were used to create the new header
    df = df.iloc[number_of_top_rows_to_merge:]

    # Set the new header as the df header
    df.columns = header
    
    return df

def translate_non_english_columns(df, non_english_column_references):
    translations = {}
    translate_client = translate.Client()
    for col in non_english_column_references:
        texts = df.iloc[:, col['column_index']].unique()
        texts = [t.strip(' .-;,!\n\t') for t in texts]
        for text in texts:
            if not text:
                continue
            date_check_text = text.replace('/', ' ').replace('-', '')
            if not date_check_text.replace(' ', '').isnumeric() and len(text) > 5:
                try:
                    source_language = langcodes.find(col['language']).language
                    translation = translate_client.translate(text, target_language='en', source_language=source_language)
                except LookupError:
                    translation = translate_client.translate(text, target_language='en')
                translations[text] = translation['translatedText']
    print(translations)
    return df.replace(translations)

def drop_columns_rows(df, row_indexes, column_indexes):
    return df

def merge_rows(df, row_indexes):
    return df

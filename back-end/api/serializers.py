from api.models import Dataset, Conversation, Message, Task
from rest_framework import serializers
from api.external_apis import openai, openai_fake_functions as fake
import pandas as pd
from pprint import pprint


# class MessageSerializerForGPT(serializers.ModelSerializer):
#     class Meta:
#         model = Message
#         fields = ['content', 'role']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class ConversationSerializer(serializers.ModelSerializer):
    message_set = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['id', 'dataset', 'created', 'task', 'updated_df_sample', 'status', 'message_set']


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'

    def create(self, data):
        df = _read_file(data['file'].file)
        data['shape'] = df.shape

        rows_minimum = 4

        # Check uploaded sheet has enough rows to work with
        if len(df) < rows_minimum:
            raise serializers.ValidationError(f"Your dataset has fewer than {rows_minimum} rows, are you sure you uploaded the right thing? I need a larger spreadsheet to be able to help you with publication.")
        
        # Reduce to something near the openai character count limit and check there are still enough rows
        sample = _limit_dataframe_characters(df)
        print(f'Number of rows: {len(df)}')
        if len(df) < rows_minimum:
            raise serializers.ValidationError(f"You have too many characters per row on your spreadsheet. I'm using OpenAI's GPT API and unfortunately there's a character limit on what I can process. When working with a dataframe as large as yours I usually take a small sample of a few rows so I am within the character count limit, but in your case I only have {len(df)} rows to work with. Can you reduce the amount of text in some of the columns, or drop some columns? Please upload a new sheet.")
        data['df_sample'] = sample.to_json(force_ascii=False) #orient='values'

        # Check there's a scientific name
        text = f'Dataframe: {data["df_sample"]} --- Is there at least one column containing either a scientific name string such as a latin name (can be for phylum, family, genus, species, subspecies, etc), or a scientificNameID such as a BOLD ID or an LSID? Reply with "yes" or "no", and no other text.'
        response = openai.chat_completion([Message(content=text, role=Message.Role.SYSTEM)])  # For some reason to work consistently this has to be system i think?
        if 'no' in response['choices'][0]['message']['content'].lower():
            raise serializers.ValidationError('It looks as if your data does not contain a scientificName or scientificNameID. It\'s only possible to publish biodiversity data linked to species on <a href="https://gbif.org" target="_blank">gbif.org</a>.')
        
        # Check there's at least one header row
        text = f'Dataframe: {data["df_sample"]} --- Is the top row a header row? Reply with "yes" or "no", and no other text.'
        response = openai.chat_completion([Message(content=text, role=Message.Role.SYSTEM)])
        if 'no' in response['choices'][0]['message']['content'].lower():
            raise serializers.ValidationError("There doesn't appear to be a header row in your data. Please add one, ideally with darwin core terms, and reupload.")
        sample = sample.rename(columns=sample.iloc[0]).drop(sample.index[0]).reset_index(drop=True)
        data['df_sample'] = sample.to_json(force_ascii=False)

        # Create the corresponding cleaning task conversations, but don't start them
        dataset = Dataset.objects.create(**data)
        for task in Task.objects.all():
            Conversation.objects.create(dataset=dataset, task=task)
        return dataset


def _read_file(file):
    # Throw an error if not csv or xlsx
    # process xlsx - i guess there needs to be a chatgpt function to join multiple sheets 
    # Your task is to try to join these different dataframes, imported as separate sheets from an excel spreadsheet. The main sheet should have a species name... something
    # try:
    df = pd.read_csv(file, skip_blank_lines=True, header=None)
    return df

def _limit_dataframe_characters(df, max_characters=3000):
    # Calculate the target character count per section (top and bottom)
    target_characters_per_section = max_characters // 2
    
    # Convert the DataFrame to a string representation
    df_str = df.to_string(index=False)
    
    # Check if the DataFrame already fits within the character limit
    if len(df_str) <= max_characters:
        return df
    
    # Calculate the reduction factor to scale down the rows
    reduction_factor = target_characters_per_section / 2 / len(df_str)
    
    # Calculate the reduced number of rows
    reduced_n = int(len(df) * reduction_factor)
    
    # Get the top and bottom sections of the DataFrame
    top_df = df.head(reduced_n)
    bottom_df = df.tail(reduced_n)
    
    # Convert the top and bottom sections to string representations
    top_df_str = top_df.to_string(index=False)
    bottom_df_str = bottom_df.to_string(index=False)
    
    # Calculate the remaining available characters
    remaining_characters = max_characters - len(top_df_str) - len(bottom_df_str)
    
    # Calculate the maximum number of rows to fit the remaining characters
    max_rows_to_fit_remaining = remaining_characters // len(df.columns)
    
    # Reduce the number of rows if necessary to fit the remaining characters
    if len(df) > max_rows_to_fit_remaining:
        reduced_n = max_rows_to_fit_remaining
    
    # Get the reduced DataFrame
    reduced_df = df.head(reduced_n)
    
    return reduced_df

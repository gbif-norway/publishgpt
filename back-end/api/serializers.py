from api.models import Dataset, DataFrame, Worker, Message
from rest_framework import serializers
import pandas as pd
import numpy as np
from api.helpers.df import trim_dataframe


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'

    def create(self, data):
        try:
            df = pd.read_csv(data['file'].file, header=None, dtype='str')
            if len(df) < 4:
                raise serializers.ValidationError(f"Your dataset has only {len(df)} rows, are you sure you uploaded the right thing? I need a larger spreadsheet to be able to help you with publication.")
            dfs = {'[None]': df}
        except:
            dfs = pd.read_excel(data['file'].file, header=None, dtype='str', sheet_name=None)

        dataset = Dataset.objects.create(**data)

        for sheet_name, df in dfs.items():
            raw_df = trim_dataframe(df)


            # df = DataFrame.objects.create(dataset=dataset, sheet_name=sheet_name, df=df)


        return dataset


class DataFrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFrame
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class WorkerSerializer(serializers.ModelSerializer):
    message_set = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Worker
        fields = '__all__'

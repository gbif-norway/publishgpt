from api.models import Dataset, DataFrame, Worker, Message, Function
from rest_framework import serializers
import pandas as pd
import numpy as np


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
            df.replace('', np.nan, inplace=True)
            df.dropna(how='all', axis=0, inplace=True) # rows
            df.dropna(how='all', axis=1, inplace=True) # columns
            df.replace(np.nan, '', inplace=True)
            df = DataFrame.objects.create(dataset=dataset, sheet_name=sheet_name, df=df)
            # import pdb; pdb.set_trace()
            df.generate_description_and_problems()  # Yes future Rukaya, I am certain that this needs to happen w/out opportunity for user feedback. Please trust me and don't go down this rabbit hole again.

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


class FunctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Function
        fields = '__all__'

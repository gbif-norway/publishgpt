from api.models import Dataset, Table, Agent, Message, Task
from rest_framework import serializers
import pandas as pd


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'name', 'per_table', 'attempt_autonomous']


class TableSerializer(serializers.ModelSerializer):
    df_str = serializers.CharField(source='df', read_only=True)

    class Meta:
        model = Table
        fields = ['id', 'created_at', 'updated_at', 'dataset', 'title', 'df_str', 'description', 'df_json']


class TableShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'title', 'updated_at']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class AgentSerializer(serializers.ModelSerializer):
    message_set = MessageSerializer(many=True, read_only=True)
    task = TaskSerializer(read_only=True)

    class Meta:
        model = Agent
        fields = '__all__'


class DatasetSerializer(serializers.ModelSerializer):
    agent_set = AgentSerializer(many=True, read_only=True)
    table_set = serializers.SerializerMethodField()

    def get_table_set(self, obj):
        tables = Table.objects.filter(dataset=obj).order_by('id')
        serializer = TableShortSerializer(tables, many=True, read_only=True)
        return serializer.data

    class Meta:
        model = Dataset
        fields = '__all__'

    def create(self, data):
        try:
            df = pd.read_csv(data['file'].file, header=None, dtype='str')
            if len(df) < 4:
                raise serializers.ValidationError(f"Your dataset has only {len(df)} rows, are you sure you uploaded the right thing? I need a larger spreadsheet to be able to help you with publication.")
            dfs = {data['file'].name: df}
        except:
            dfs = pd.read_excel(data['file'].file, header=None, dtype='str', sheet_name=None)

        dataset = Dataset.objects.create(**data)
        task = Task.objects.get(pk=1)
        for sheet_name, df in dfs.items():
            if not df.empty:
                table = Table.objects.create(dataset=dataset, title=sheet_name, df=df)
                Agent.create_with_system_message(dataset=dataset, task=task, tables=[table])
        return dataset

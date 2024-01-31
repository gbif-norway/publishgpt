from api.models import Dataset, Table, Agent, Message, Task, MessageTableAssociation
from rest_framework import serializers
import pandas as pd
from api.helpers.df_helpers import extract_sub_tables


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'name', 'per_table']


class TableSerializer(serializers.ModelSerializer):
    df_str = serializers.CharField(source='df', read_only=True)

    class Meta:
        model = Table
        fields = ['id', 'created_at', 'dataset', 'title', 'df_str', 'description', 'df_json']


class TableShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'title']


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
        task = Task.objects.get(name='extract_subtables')
        for sheet_name, df in dfs.items():
            if not df.empty:
                table = Table.objects.create(dataset=dataset, title=sheet_name, df=df)
                agent = Agent.create_with_system_message(dataset=dataset, task=task, tables=[table])
                sub_tables = extract_sub_tables(table.df)
                Message.objects.create(agent=agent, function_name='ExtractSubTables', role=Message.Role.FUNCTION, content='', faked=True)
                text = f'I just had a look at your spreadsheet "{table.title}". An important step in publishing your data is separating out each table so we can handle them separately. A single table is one block of related data with consistent columns and rows. A good rule of thumb is that if you find yourself drawing a border as a divider or using formatting to split up your data, that should be treated as two tables.'

                if len(sub_tables) > 1:
                    table.delete()
                    distinct_tables = []
                    for idx, new_df in enumerate(sub_tables):
                        new_table = Table.objects.create(dataset=dataset, title=f'{table.title} - {idx}', df=new_df)
                        distinct_tables.append(new_table)

                    snapshots = '\n\n'.join([f'Sub-table #{idx} - (Table.id: {d.id})\n{d.str_snapshot}' for idx, d in enumerate(distinct_tables)])
                    if len(snapshots) > 4000:
                        snapshots = snapshots[0:4000] + '\n...'
                    text += f'Based on the empty rows & columns which appear to be acting as "dividers", I have divided the table into {len(distinct_tables)} new different, separate tables:\n{snapshots}\n\nIs this correct? Are any other separate sub-tables I missed which should be split off?'
                    Message.objects.create(agent=agent, role=Message.Role.ASSISTANT, content=text, faked=True)
                else:
                    text += 'It looks like this is a single table to me, is that right?'
                    Message.objects.create(agent=agent, role=Message.Role.ASSISTANT, content=text, faked=True)

        return dataset



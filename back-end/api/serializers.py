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
        fields = ['id', 'created_at', 'dataset', 'title', 'df_str', 'description', 'deleted_at', 'stale_at', 'df_json']


class TableShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'title']


class MessageTableAssociationSerializer(serializers.ModelSerializer):
    table = TableShortSerializer(read_only=True)

    class Meta:
        model = MessageTableAssociation
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    message_table_associations = MessageTableAssociationSerializer(source='messagetableassociation_set', many=True, read_only=True)

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
        for sheet_name, df in dfs.items():
            Table.objects.create(dataset=dataset, title=sheet_name, df = df)
        task = Task.objects.get(name='extract_subtables')
        agents = task.create_agents_with_system_messages(dataset)  # One agent per sheet

        for agent in agents:
            working_table = agent.message_set.first().tables.first()  # There should only be the system message, and there should only be one table associated with it
            sub_tables = extract_sub_tables(working_table.df)
            function_message = Message.objects.create(agent=agent, function_name='ExtractSubTables', role=Message.Role.FUNCTION, content='', faked=True) 
            
            text = f'I just had a look at your spreadsheet "{working_table.title}". An important step in publishing your data is separating out each table so we can handle them separately. '
            
            if len(sub_tables) > 1:
                working_table.soft_delete()
                MessageTableAssociation.objects.create(table=working_table, message=function_message, operation=MessageTableAssociation.Operation.DELETE)

                distinct_tables = []
                for idx, new_df in enumerate(sub_tables):
                    new_table = Table.objects.create(dataset=dataset, title=f'{working_table.title} - {idx}', df=new_df)
                    distinct_tables.append(new_table)
                    MessageTableAssociation.objects.create(table=new_table, message=function_message, operation=MessageTableAssociation.Operation.CREATE)
                
                snapshots = '\n\n'.join([f'Sub-table #{idx} - (Table.id: {d.id})\n{d.str_snapshot}' for idx, d in enumerate(distinct_tables)]) 
                if len(snapshots) > 4000:
                    snapshots = snapshots[0:4000] + '\n...'
                text += f'Based on the empty rows & columns which appear to be acting as "dividers", I have divided the table into {len(distinct_tables)} new different, separate tables:\n{snapshots}\n\nIs this correct? Are any other separate sub-tables I missed which should be split off?'
                Message.objects.create(agent=agent, role=Message.Role.ASSISTANT, content=text, faked=True)  
            else:
                text += 'It looks like this is a single table to me, is that right?'
                Message.objects.create(agent=agent, role=Message.Role.ASSISTANT, content=text, faked=True) 

        return dataset



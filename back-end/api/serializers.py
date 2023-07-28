from api.models import Dataset, Table, Agent, Message, Task, MessageTableAssociation
from rest_framework import serializers
import pandas as pd
from api.helpers.df_helpers import trim_dataframe, extract_sub_tables
from django.template.loader import render_to_string
from datetime import datetime


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'name', 'per_table']


class MessageTableAssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTableAssociation
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    tables = MessageTableAssociationSerializer(source='messagetableassociation_set', many=True, read_only=True)

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
            dfs = {'[None]': df}
        except:
            dfs = pd.read_excel(data['file'].file, header=None, dtype='str', sheet_name=None)
        
        dataset = Dataset.objects.create(**data)

        for sheet_name, df in dfs.items():
            # Try to extract any sub tables which exist in the sheet. Because people do this, for some reason. We need to treat each one separately.
            distinct_tables = []
            for new_df in extract_sub_tables(df):
                distinct_tables.append(Table.objects.create(dataset=dataset, title=sheet_name, df=trim_dataframe(new_df)))
            
            task = Task.objects.get(name='extract_subtables')
            agent = task.create_agents_with_system_messages(dataset)[0]  # Only 1 agent should get created per sheet for this task
                
            if len(distinct_tables) == 1:
                agent.completed_at = datetime.now()
                agent.save()
            else:
                Message.objects.create(agent=agent, function_name='ExtractSubTables', role=Message.Role.FUNCTION, content=distinct_tables) 
                snapshots = '\n\n'.join([f'Sub-table #{idx} - (Table.id: {d.id})\n{d.str_snapshot}' for idx, d in enumerate(distinct_tables)]) 
                if len(snapshots) > 4000:
                    snapshots = snapshots[0:4000] + '\n...'
                explain_extracted_subtables = 'I just had a look at your spreadsheet "{title}". An important step in publishing your data is separating out each table so we can handle them separately. Based on the empty rows & columns which appear to be acting as "dividers", it looks like it actually contains {len} different, separate tables:\n{snapshots}\n\nIs this correct? Please let me know: a) if there are any separate sub-tables I missed which should be split off, and b) if there are any sub-tables that were incorrectly split, which should actually be joined to other sub-tables. '
                text = explain_extracted_subtables.format(title=sheet_name, len=len(distinct_tables), snapshots=snapshots)
                Message.objects.create(agent=agent, role=Message.Role.ASSISTANT, content=text)  
        
        return dataset


class TableSerializer(serializers.ModelSerializer):
    df_str = serializers.CharField(source='df', read_only=True)

    class Meta:
        model = Table
        fields = ['id', 'created_at', 'dataset', 'title', 'df_str', 'description', 'deleted_at', 'stale_at', 'df_json']


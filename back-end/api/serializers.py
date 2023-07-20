from api.models import Dataset, DatasetFrame, Agent, Message, Task
from rest_framework import serializers
import pandas as pd
from api.helpers.df_helpers import trim_dataframe, get_datasetframe_sub_tables
from api.openai_wrapper import prompts, functions


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
            ds_frame = DatasetFrame.objects.create(dataset=dataset, title=sheet_name, df=trim_dataframe(df))
            sub_dsfs = get_datasetframe_sub_tables(ds_frame)

            if len(sub_dsfs) > 1:
                # Start an agent to handle the sub table extraction
                agent = Agent.create_with_task_and_datasetframes(
                    dataset=dataset,
                    task = Task.objects.get(name='extract_subtables')
                )

                # Give the agent access to the results of the extract subtable function
                Message.objects.create(agent=agent, 
                                       function_name='ExtractSubTables',
                                       role=Message.Role.FUNCTION, 
                                       content=sub_dsfs) 

                snapshots = '\n\n'.join([f'Sub-table #{idx} - (DatasetFrame.id: {d["key"]})\n```{d["preview"]}```' for idx, d in enumerate(sub_dsfs)]) 
                explain_extracted_subtables = 'I just had a look at your spreadsheet "{title}". Based on the empty rows & columns which appear to be acting as "dividers" between the sub-tables, I think it contains {len} different, separate tables:\n{snapshots}\n\nIs this correct? Please let me know: a) if there are any separate sub-tables I missed which should be split off, and b) if there are any sub-tables that were incorrectly split, which should actually be joined to other sub-tables. An important step in publishing your data is getting every table loaded separately. '
                Message.objects.create(agent=agent, 
                                       role=Message.Role.ASSISTANT, 
                                       content=explain_extracted_subtables.format(title=ds_frame.title, len=len(sub_dsfs), snapshots=snapshots))  

        return dataset


class DatasetFrameSerializer(serializers.ModelSerializer):
    df_str = serializers.CharField(source='df', read_only=True)

    class Meta:
        model = DatasetFrame
        fields = fields = ['id', 'created', 'dataset', 'title', 'df_str', 'description', 'problems', 'parent']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class AgentSerializer(serializers.ModelSerializer):
    message_set = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Agent
        fields = '__all__'
    

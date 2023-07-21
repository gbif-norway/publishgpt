from api.models import Dataset, DatasetFrame, Agent, Message, Task, AgentDatasetFrame
from rest_framework import serializers
import pandas as pd
from api.helpers.df_helpers import trim_dataframe, get_datasetframe_sub_tables
from api.openai_wrapper import prompts, functions
from django.template.loader import render_to_string


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class AgentSerializer(serializers.ModelSerializer):
    message_set = MessageSerializer(many=True, read_only=True)
    
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
            dataset_frame = DatasetFrame.objects.create(dataset=dataset, title=sheet_name, df=trim_dataframe(df))

            # Try to extract any sub tables which exist in the sheet. Because people do this, for some reason. We need to treat each one separately.
            sub_dataset_frames = get_datasetframe_sub_tables(dataset_frame)

            if len(sub_dataset_frames) > 1:
                # Start an agent to handle the sub table extraction
                task = Task.objects.get(name='extract_subtables')
                agent = Agent.objects.create(_functions=task.functions, dataset=dataset, task=task)

                for datasetframe in sub_dataset_frames:
                    AgentDatasetFrame.objects.create(agent=agent, dataset_frame_id=datasetframe['id'])
                system_message = render_to_string('single_df.txt', context={'agent': agent, 'agent_datasetframes': [dataset_frame] })
                Message.objects.create(agent=agent, content=system_message, role=Message.Role.SYSTEM)

                # Give the agent access to the results of the extract subtable function
                Message.objects.create(agent=agent, function_name='ExtractSubTables', role=Message.Role.FUNCTION, content=sub_dataset_frames) 

                snapshots = '\n\n'.join([f'Sub-table #{idx} - (DatasetFrame.id: {d["id"]})\n```{d["df_preview"]}```' for idx, d in enumerate(sub_dataset_frames)]) 
                explain_extracted_subtables = 'I just had a look at your spreadsheet "{title}". Based on the empty rows & columns which appear to be acting as "dividers" between the sub-tables, I think it contains {len} different, separate tables:\n{snapshots}\n\nIs this correct? Please let me know: a) if there are any separate sub-tables I missed which should be split off, and b) if there are any sub-tables that were incorrectly split, which should actually be joined to other sub-tables. An important step in publishing your data is getting every table loaded separately. '
                Message.objects.create(agent=agent, 
                                       role=Message.Role.ASSISTANT, 
                                       content=explain_extracted_subtables.format(title=dataset_frame.title, len=len(sub_dataset_frames), snapshots=snapshots))  

        return dataset


class DatasetFrameSerializer(serializers.ModelSerializer):
    df_str = serializers.CharField(source='df', read_only=True)

    class Meta:
        model = DatasetFrame
        fields = fields = ['id', 'created', 'dataset', 'title', 'df_str', 'description', 'problems', 'parent']

    

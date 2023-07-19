from api.models import Dataset, DatasetFrame, Agent, Message
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
            dsf = DatasetFrame.objects.create(dataset=dataset, title=sheet_name, df=trim_dataframe(df))
            sub_dsfs = get_datasetframe_sub_tables(dsf)

            if len(sub_dsfs) > 1:
                # Start an agent to handle the sub table extraction
                agent = Agent.create_with_system_message(
                    system_message = prompts.extract_subtables.format(**{ 'df_id': dsf.id, 'ds_id': dataset.id, 'title': dsf.title, 'snapshot': str(dsf) }),
                    _functions = [functions.Python.__name__],
                    dataset=dataset
                )

                # Give the agent access to the results of the extract subtable function
                Message.objects.create(agent=agent, 
                                       function_name='ExtractAndSaveSubtableDatasetFramesForUserFeedback',
                                       role=Message.Role.FUNCTION, 
                                       content=sub_dsfs)  

                # snapshots = f'\n\n'.join([f'DatasetFrame ID: {x.id}\n{trunc_df_to_string(x.df)}' for x in sub_df_objects])
                #,prompts.explain_extracted_subtables.format(**{ 'len': len(sub_dfs), 'snapshots': snapshots, 'title': df.title }))

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
    

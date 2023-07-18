from api.models import Dataset, DataFrame, Agent, Message
from rest_framework import serializers
import pandas as pd
from api.helpers.df_helpers import trim_dataframe, extract_sub_tables_based_on_null_boundaries, trunc_df_to_string
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
            df = DataFrame.objects.create(dataset=dataset, title=sheet_name, df=trim_dataframe(df))

            # Create agents to handle multiple tables in one sheet
            sub_dfs = extract_sub_tables_based_on_null_boundaries(df.df)
            if len(sub_dfs) > 1:
                agent = Agent.create_with_system_message(
                    system_message = prompts.extract_subtables.format(**{ 'df_id': df.id, 'ds_id': dataset.id, 'title': df.title, 'snapshot': trunc_df_to_string(df) }),
                    _functions = [functions.Python.classname]
                )
                snapshots = '\n\n'.join([trunc_df_to_string(x) for x in sub_dfs])
                Message.objects.create(Agent=agent, 
                                       role=Message.Role.ASSISTANT, 
                                       content=prompts.explain_extracted_subtables.format(**{ 'len': len(sub_dfs), 'snapshots': snapshots }))

        return dataset


class DataFrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFrame
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class AgentSerializer(serializers.ModelSerializer):
    message_set = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Agent
        fields = '__all__'

from rest_framework import viewsets, status
from api.serializers import DatasetSerializer, DataFrameSerializer, MessageSerializer, AgentSerializer
from api.models import Dataset, DataFrame, Message, Agent, Function
from rest_framework.response import Response
from rest_framework.decorators import action 
from api.openai_wrapper import functions, prompts
from helpers import df_helpers


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filterset_fields = ['created', 'orcid', 'master_Agent']

    @action(detail=True)
    def get_next_task_agent(self, request, *args, **kwargs):
        pass


class DataFrameViewSet(viewsets.ModelViewSet):
    queryset = DataFrame.objects.all()
    serializer_class = DataFrameSerializer
    filterset_fields = ['dataset', 'sheet_name']


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filterset_fields = '__all__'


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    filterset_fields = '__all__'

    @action(detail=True)
    def chat(self, request, *args, **kwargs):
        agent = self.get_object()
        return_message = agent.run(allow_user_feedack=True)
        if return_message:
            serializer = MessageSerializer(return_message)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(None, status=status.HTTP_404_NOT_FOUND)

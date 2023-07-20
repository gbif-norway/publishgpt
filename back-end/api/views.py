from rest_framework import viewsets, status
from api.serializers import DatasetSerializer, DatasetFrameSerializer, MessageSerializer, AgentSerializer
from api.models import Dataset, DatasetFrame, Message, Agent
from rest_framework.response import Response
from rest_framework.decorators import action 
from django.contrib.postgres.fields import ArrayField
import django_filters as filters


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filterset_fields = ['created', 'orcid']

    @action(detail=True)
    def get_or_create_next_agent(self, request, *args, **kwargs):
        dataset = self.get_object()
        serializer = AgentSerializer(dataset.get_or_create_next_agent())
        return Response(serializer.data, status=status.HTTP_200_OK)


class DatasetFrameViewSet(viewsets.ModelViewSet):
    queryset = DatasetFrame.objects.all()
    serializer_class = DatasetFrameSerializer
    filterset_fields = ['dataset', 'title']


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filterset_fields = '__all__'


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    filterset_overrides = {
       ArrayField: {
            'filter_class': filters.CharFilter,
            'extra': lambda f: {
                'lookup_expr': 'icontains',
            },
        },
    }

    @action(detail=True)
    def chat(self, request, *args, **kwargs):
        agent = self.get_object()
        next_assistant_message = agent.get_next_assistant_message_for_user()
        if next_assistant_message:
            serializer = MessageSerializer(next_assistant_message)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(None, status=status.HTTP_404_NOT_FOUND)  # This should happen only when the dataset is ready for publication

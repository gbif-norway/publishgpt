from rest_framework import viewsets, status
from api.serializers import DatasetSerializer, TableSerializer, MessageSerializer, AgentSerializer, TaskSerializer
from api.models import Dataset, Table, Message, Agent, Task
from rest_framework.response import Response
from rest_framework.decorators import action 
from django.shortcuts import get_object_or_404


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filterset_fields = ['created_at', 'orcid']

    @action(detail=True)
    def next_agent(self, request, *args, **kwargs):
        dataset = self.get_object()
        serializer = AgentSerializer(dataset.next_agent())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True)
    def refresh(self, request, *args, **kwargs):
        dataset = self.get_object()

        # Do a refresh of agents and messages, so we get the next one of each if necessary
        next_agent = dataset.next_agent()
        next_message = next_agent.next_message()
        dataset.refresh_from_db()
        
        serializer = self.get_serializer(dataset)
        return Response(serializer.data)

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    filterset_fields = ['dataset', 'title']
    ordering = ['-updated_at']


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filterset_fields = '__all__'


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filterset_fields = '__all__'


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    filterset_fields = ['created_at', 'completed_at', 'dataset', 'task']

    @action(detail=True)
    def next_message(self, request, *args, **kwargs):
        agent = self.get_object()
        serializer = MessageSerializer(agent.next_message())
        return Response(serializer.data, status=status.HTTP_200_OK)
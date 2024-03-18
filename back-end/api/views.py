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

    def retrieve(self, request, pk=None):
        queryset = Dataset.objects.all()
        dataset = get_object_or_404(queryset, pk=pk)
        dataset.update_agents()
        dataset.refresh_from_db()
        serializer = DatasetSerializer(dataset)
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

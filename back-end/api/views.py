from rest_framework import viewsets, status
from api.serializers import DatasetSerializer, DatasetFrameSerializer, MessageSerializer, AgentSerializer
from api.models import Dataset, DatasetFrame, Message, Agent
from rest_framework.response import Response
from rest_framework.decorators import action 
from api.openai_wrapper import functions, prompts
from api.helpers import df_helpers
from django.contrib.postgres.fields import ArrayField
import django_filters as filters


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filterset_fields = ['created', 'orcid']

    @action(detail=True)
    def get_next_task_agent(self, request, *args, **kwargs):
        pass


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
    # filterset_fields = '__all__'
    # filter_backends = (filters.rest_framework.DjangoFilterBackend,)
    # filter_fields = ['dataset', 'created', 'task_complete']

    @action(detail=True)
    def chat(self, request, *args, **kwargs):
        agent = self.get_object()
        return_message = agent.run(allow_user_feedack=True)
        import pdb; pdb.set_trace()
        if return_message:
            serializer = MessageSerializer(return_message)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(None, status=status.HTTP_404_NOT_FOUND)

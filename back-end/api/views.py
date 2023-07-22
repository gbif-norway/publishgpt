from rest_framework import viewsets, status
from api.serializers import DatasetSerializer, DatasetFrameSerializer, MessageSerializer, AgentSerializer, TaskSerializer
from api.models import Dataset, DatasetFrame, Message, Agent, Task
from rest_framework.response import Response
from rest_framework.decorators import action 


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filterset_fields = ['created', 'orcid']

    @action(detail=True)
    def completed_agents(self, request, *args, **kwargs):
        dataset = self.get_object()
        completed_agents = dataset.agent_set.exclude(completed=None).all()
        serializer = AgentSerializer(completed_agents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True)
    def get_or_create_next_agent(self, request, *args, **kwargs):
        dataset = self.get_object()

        next_agent = dataset.agent_set.filter(completed=None).first()
        if not next_agent:
            print('No next agent found, making new agent for new task')
            last_completed_agent = dataset.agent_set.exclude(completed=None).first()
            if last_completed_agent:
                last_task_id = last_completed_agent.task.id
                next_task = Task.objects.filter(id__gt=last_task_id).first()
                if next_task:
                    new_agents = next_task.create_agents(dataset=dataset)
                    print('recursing')
                    return self.get_or_create_next_agent(request)
                else:
                    return Response('ALL TASKS COMPLETE', status=status.HTTP_200_OK)
            else:
                raise Exception('Agent set for this dataset appears to be empty')

        next_agent.get_next_assistant_message_for_user()
        serializer = AgentSerializer(next_agent.refresh_from_db())
        return Response(serializer.data, status=status.HTTP_200_OK)


class DatasetFrameViewSet(viewsets.ModelViewSet):
    queryset = DatasetFrame.objects.all()
    serializer_class = DatasetFrameSerializer
    filterset_fields = ['dataset', 'title']


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
    filterset_fields = ['created', 'completed', 'dataset', 'task']

    @action(detail=True, methods=['get', 'post'])
    def chat(self, request, *args, **kwargs):
        if self.request.method == 'POST':
            agent = self.get_object()
            content = request.data.get('content', None)
            if 'content' in request.POST:  # I think this is how it is from DRF
                content = request.POST['content']
            Message.objects.create(agent=agent, content=content, role=Message.Role.USER, display_to_user=True)
            reply = agent.run()
            serializer = MessageSerializer(reply)
            return Response(serializer.data, status=status.HTTP_200_OK)
        if self.request.method == 'GET':
            agent = self.get_object()
            next_assistant_message = agent.get_next_assistant_message_for_user()
            if next_assistant_message:
                serializer = MessageSerializer(next_assistant_message)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(None, status=status.HTTP_404_NOT_FOUND)  # This should happen only when the dataset is ready for publication

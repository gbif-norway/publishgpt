from rest_framework import viewsets, status
from api.serializers import DatasetSerializer, TableSerializer, MessageSerializer, AgentSerializer, TaskSerializer
from api.models import Dataset, Table, Message, Agent, Task
from rest_framework.response import Response
from rest_framework.decorators import action 


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filterset_fields = ['created_at', 'orcid']

    @action(detail=True)
    def completed_agents(self, request, *args, **kwargs):
        dataset = self.get_object()
        completed_agents = dataset.agent_set.exclude(completed_at=None).all()
        serializer = AgentSerializer(completed_agents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True)
    def get_or_create_next_agent(self, request, *args, **kwargs):
        dataset = self.get_object()

        next_agent = dataset.agent_set.filter(completed_at=None).first()
        if not next_agent:
            last_completed_agent = dataset.agent_set.exclude(completed_at=None).last()
            print(f'No next agent found, making new agent for new task based on {last_completed_agent}')
            if last_completed_agent:
                last_task_id = last_completed_agent.task.id
                print(f'Last task id {last_task_id}')
                next_task = Task.objects.filter(id__gt=last_task_id).first()
                print(f'Next task id {next_task.id}, {next_task.name}')
                if next_task:
                    next_task.create_agents_with_system_messages(dataset=dataset)
                    print('recursing')
                    return self.get_or_create_next_agent(request)
                else:
                    return Response('ALL TASKS COMPLETE', status=status.HTTP_200_OK)
            else:
                raise Exception('Agent set for this dataset appears to be empty')

        next_message = next_agent.get_next_assistant_message_for_user()
        if next_message is None:
            return self.get_or_create_next_agent(request)
        print('next agent about to be returned')
        # import pdb; pdb.set_trace()
        next_agent.refresh_from_db()
        serializer = AgentSerializer(next_agent)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
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
    filterset_fields = ['created_at', 'completed_at', 'dataset', 'task']

    @action(detail=True)
    def next_agent_message(self, request, *args, **kwargs):
        agent = self.get_object()
        next_assistant_message = agent.get_next_assistant_message_for_user()
        if next_assistant_message:
            serializer = MessageSerializer(next_assistant_message)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'id': None}, status=status.HTTP_200_OK)  # This should happen only when the dataset is ready for publication

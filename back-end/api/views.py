from rest_framework import viewsets, permissions, authentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.serializers import DatasetSerializer, ConversationSerializer, MessageSerializer, TaskSerializer
from api.models import Dataset, Conversation, Message, Task
from api.external_apis import openai
from api.external_apis import openai_fake_functions as fake
from rest_framework.decorators import action 


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all().order_by('-created')
    serializer_class = DatasetSerializer
    # permission_classes = [permissions.IsAuthenticated]
    # authentication_classes = [authentication.TokenAuthentication]

    @action(detail=True)
    def next_conversation_task(self, request, *args, **kwargs):
        dataset = self.get_object()
        next_conversation = dataset.get_next_conversation_task()
        if next_conversation:
            return Response(ConversationSerializer(next_conversation).data, status=status.HTTP_200_OK)
        return Response(None, status=status.HTTP_404_NOT_FOUND)


class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all().order_by('-created')
    serializer_class = ConversationSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by('-pk')
    serializer_class = TaskSerializer


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().order_by('-pk')
    serializer_class = MessageSerializer

    @action(detail=True)
    def post_message_and_get_reply(self, request, *args, **kwargs):
        conversation = self.get_object()

        serialized_user_message = MessageSerializer(instance=None, data=request.data)
        if serialized_user_message.is_valid():
            serialized_user_message['role'] = Message.Role.USER
            user_message = serialized_user_message.save()
            
            # Store the assistant reply
            assistant_message = Message(role=Message.Role.ASSISTANT)
            assistant_message.gpt_response = openai.chat_completion_with_functions(
                messages=conversation.message_set, 
                functions=conversation.task.function_objects, 
                model=conversation.task.gpt_model
            )
            assistant_message.save()

            if conversation.status != Conversation.Status.COMPLETED:
                # Need an adjustment here so we return an html table for the df_sample, if one has been set
                return Response(MessageSerializer(assistant_message).data, status=status.HTTP_200_OK)
        
            next_message = conversation.dataset.start_next_task_conversation()
            if next_message:
                return Response(MessageSerializer(next_message).data, status=status.HTTP_200_OK)
            
            final_message = {'message': 'Congratulations! Your dataset has been published something something'}
            return Response(final_message, status=status.HTTP_200_OK)

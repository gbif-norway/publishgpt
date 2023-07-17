from rest_framework import viewsets, status
from api.serializers import DatasetSerializer, DataFrameSerializer, MessageSerializer, WorkerSerializer
from api.models import Dataset, DataFrame, Message, Worker, Function
from rest_framework.response import Response
from rest_framework.decorators import action 
from api.openai_wrapper import functions, prompts


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    filterset_fields = ['created', 'orcid', 'master_worker']

    @action(detail=True)
    def create_worker(self, request, *args, **kwargs):
        dataset = self.get_object()
        if False:
            prompt_args = {
                'dataset_id': dataset.id,
                'df_sample_str': '\n\n'.join([x.get_summary_str() for x in dataset.dataframe_set.all()])
            }
            worker = Worker.objects.create(
                task=prompts.generate_plan.format(**prompt_args),
                stop_function=Function.objects.get(pk=functions.save_dataset_plan.openai_schema['name'])
            )
            worker.functions.add(functions.allocate_dataset_core_and_extensions.openai_schema['name'])
            worker.functions.add(functions.query_dataframe.openai_schema['name'])
            return_message = worker.run(allow_user_feedack=True)
            
            if return_message:
                serializer = MessageSerializer(return_message)
                return Response(serializer.data, status=status.HTTP_200_OK)
            # dataset = db_models.Dataset.objects.get(id=dataset.id)
            dataset.refresh_from_db()
            print(dataset.master_worker)
        plan_text = '\n\n'.join([f'{d["plan_title"]} (involves df_ids: {d["df_ids"]}): {d["plan_step"]}' for d in dataset.plan])
        dfs_list = dataset.dataframe_set.all().values_list('id', flat=True)
        dataframe_ids = map(str, dfs_list)
        task_text = prompts.main_worker.format(plan=plan_text, 
                                               dataset_id=dataset.id,
                                               dataframes_no=len(dfs_list), 
                                     dataframe_ids=', '.join(dataframe_ids), 
                                     core=dataset.dwc_core, 
                                     extensions=', '.join(dataset.dwc_extensions))
        # Spawn master worker with plan
        # last_item = dataset.plan.pop()
        # plan_item = dataset.plan[0]
        # while plan_item:
        #     stop_function = Function.objects.get(name=functions.publish_dwc.openai_schema['name'])
        #     dataset.master_worker = Worker.objects.create(task=dataset.plan, stop_function=stop_function)
        #     dataset.master_worker.functions.add(run_python_with_dataframe_orm.openai_schema['name'])
        #     dataset.save()
        import pdb; pdb.set_trace()
        stop_function = Function.objects.get(name=functions.publish_dwc.openai_schema['name'])
        dataset.master_worker = Worker.objects.create(task=task_text, stop_function=stop_function)
        dataset.master_worker.functions.add(functions.run_python_with_dataframe_orm.openai_schema['name'])
        dataset.save()
        return Response({'master_worker_id': dataset.master_worker.id}, status=status.HTTP_201_CREATED)


class DataFrameViewSet(viewsets.ModelViewSet):
    queryset = DataFrame.objects.all()
    serializer_class = DataFrameSerializer
    filterset_fields = ['dataset', 'sheet_name']


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    filterset_fields = '__all__'


class WorkerViewSet(viewsets.ModelViewSet):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer
    filterset_fields = '__all__'

    @action(detail=True)
    def run(self, request, *args, **kwargs):
        worker = self.get_object()
        return_message = worker.run(allow_user_feedack=True)
        serializer = MessageSerializer(return_message)
        return Response(serializer.data, status=status.HTTP_200_OK)
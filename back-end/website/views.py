from django.views import generic
from api.models import Dataset


class DatasetListView(generic.ListView):
    template_name = "dataset_list.html"
    context_object_name = "dataset_list"

    def get_queryset(self):
        return Dataset.objects.all()

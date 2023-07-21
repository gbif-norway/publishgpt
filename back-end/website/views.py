from django.views import generic
from api.models import Dataset
from django.shortcuts import redirect
from django.views.generic.base import TemplateView



class DatasetListView(generic.ListView):
    template_name = "dataset_list.html"
    model = Dataset


class DatasetDetailView(generic.DetailView):
    template_name = "chat.html"
    model = Dataset


class Chat(TemplateView):
    template_name = "chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['user_orcid'] = something # Maybe?
        return context

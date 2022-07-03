from django.shortcuts import render, get_object_or_404
from django.db.models import Q
import logging
from django.core.exceptions import PermissionDenied
from core.models import Analysis
from general.models import *
from django.views.generic import ListView
from django.utils.decorators import method_decorator


# Staff member check is managed at the urls
class ReviewView(ListView):
    template_name = 'core/review.html'
    context_object_name = 'context'
    model = Analysis
    ordering = 'id'

    def get_queryset(self):
        mode = self.request.GET.get('mode')
        if mode == "all":
            return Analysis.objects.all()
        return Analysis.objects.filter(auditor=self.request.user)




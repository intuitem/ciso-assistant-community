from django_filters import *

from core.models import Analysis

class AnalysisFilter(FilterSet):
    STATUS_CHOICES = (
        (True, 'Yes'),
        (False, 'No'),
    )
    is_draft = ChoiceFilter(choices=STATUS_CHOICES)
    class Meta:
        model = Analysis
        fields = ['is_draft', 'auditor', 'project']
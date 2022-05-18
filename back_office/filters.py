from django_filters import *

from core.models import Analysis

class AnalysisFilter(FilterSet):
    class Meta:
        model = Analysis
        fields = ['is_draft', 'auditor', 'project']
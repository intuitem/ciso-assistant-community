from django.forms import ModelForm, Textarea

from core.models import Analysis

class RiskAnalysisUpdateForm(ModelForm):
    class Meta:
        model = Analysis
        fields = ['is_draft', 'rating_matrix', 'comments']
        widgets = { # Tailwind Styles go here
            'comments': Textarea(attrs={'class': 'w-full rounded-md'}),
        }
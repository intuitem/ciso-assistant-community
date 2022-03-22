from django.forms import ModelForm, Select, Textarea

from core.models import Analysis, RiskInstance

class RiskAnalysisUpdateForm(ModelForm):
    class Meta:
        model = Analysis
        fields = ['is_draft', 'rating_matrix', 'comments']
        widgets = { # Tailwind Styles go here
            'comments': Textarea(attrs={'class': 'w-full rounded-md'}),
        }

class RiskInstanceUpdateForm(ModelForm):
    class Meta:
        model = RiskInstance
        fields = ['analysis', 'parent_risk', 'title', 'scenario', 'existing_measures', 'comments',
        'current_proba', 'current_impact', 'residual_proba', 'residual_impact', 'treatment']
        widgets = { # Tailwind Styles go here
            'existing_measures': Textarea(attrs={'class': 'w-full rounded-md text-sm h-32'}),
            'scenario': Textarea(attrs={'class': 'w-full rounded-md text-sm h-24'}),
            'comments': Textarea(attrs={'class': 'w-full rounded-md text-sm h-18'}),
            'parent_risk': Select(attrs={'class': 'w-full rounded-md text-sm'}),
            'current_proba': Select(attrs={'class': 'w-full rounded-md text-sm'}),
            'current_impact': Select(attrs={'class': 'w-full rounded-md text-sm'}),
            'residual_proba': Select(attrs={'class': 'w-full rounded-md text-sm'}),
            'residual_impact': Select(attrs={'class': 'w-full rounded-md text-sm'}),
            'treatment': Select(attrs={'class': 'w-full rounded-md text-sm'}),
        }
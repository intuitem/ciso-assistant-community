from dataclasses import fields
from django.forms import DateInput, DateTimeInput, ModelForm, Select, TextInput, Textarea, widgets

from django.contrib.auth.models import User, Group
from core.models import Analysis, Mitigation, RiskInstance
from general.models import Project, ProjectsGroup, Solution

class RiskAnalysisCreateForm(ModelForm):
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'is_draft', 'rating_matrix', 'comments']
        widgets = { # Tailwind Styles go here
            'comments': Textarea(attrs={'class': 'w-full rounded-md'}),
        }

class MeasureCreateForm(ModelForm):
    class Meta:
        model = Mitigation
        fields = '__all__'
        widgets = { # Tailwind Styles go here
            'comments': Textarea(attrs={'class': 'w-full rounded-md'}),
        }

class SecurityFunctionCreateForm(ModelForm):
    class Meta:
        model = Solution
        fields = '__all__'
        widgets = { # Tailwind Styles go here
            'comments': Textarea(attrs={'class': 'w-full rounded-md'}),
        }

class UserCreateForm(ModelForm):
    class Meta:
        model = User
        fields = '__all__'
        widgets = { # Tailwind Styles go here
            'comments': Textarea(attrs={'class': 'w-full rounded-md'}),
        }

class RiskAnalysisUpdateForm(ModelForm):
    class Meta:
        model = Analysis
        fields = ['is_draft', 'rating_matrix', 'comments']
        widgets = { # Tailwind Styles go here
            'comments': Textarea(attrs={'class': 'w-full rounded-md'}),
        }

class RiskInstanceCreateForm(ModelForm):
    class Meta:
        model = RiskInstance
        exclude = ['analysis', 'residual_level', 'current_level']
        
        widgets = { # Tailwind Styles go here
            'analysis': Select(attrs={'class': 'w-auto rounded-md text-sm h-32'}),
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

class RiskInstanceUpdateForm(ModelForm):
    class Meta:
        model = RiskInstance
        fields = '__all__'
        exclude = ['current_level', 'residual_level']
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

class MitigationUpdateForm(ModelForm):
    class Meta:
        model = Mitigation
        exclude = ['risk_instance']
        widgets = {
            'eta': DateInput()
        }

class ProjectsGroupUpdateForm(ModelForm):
    class Meta:
        model = ProjectsGroup
        fields = '__all__'
        widgets = { # Tailwind Styles go here
            'name': TextInput(attrs={'class': 'w-full rounded text-sm h-32 border border-gray-300'}),
            'department': TextInput(attrs={'class': 'w-full rounded text-sm h-32 border border-gray-300'}),
        }

class ProjectUpdateForm(ModelForm):
    class Meta:
        model = Project
        fields = '__all__'

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        widgets = {
            'name': TextInput(attrs={'class': 'w-full rounded text-sm border border-gray-300 h-32'}),
            'internal_id': TextInput(attrs={'class': 'w-full rounded border border-gray-300 text-sm h-32'}),
            'parent_group': Select(attrs={'class': 'w-full rounded border border-gray-300 text-sm h-32'}),
            'lc_status': Select(attrs={'class': 'w-full rounded border border-gray-300 text-sm h-32'}),
            'summary': Textarea(attrs={'class': 'w-full rounded border border-gray-300 text-sm h-32'}),
        }
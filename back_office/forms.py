from sqlite3 import Date
from django.forms import CharField, CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, widgets

from django.contrib.auth.models import User, Group
from core.models import Analysis, Mitigation, RiskAcceptance, RiskInstance
from general.models import ParentRisk, Project, ProjectsGroup, Solution

class DefaultDateInput(DateInput):
    input_type = 'date'

class StyledModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(__class__, self).__init__(*args, **kwargs)
        text_inputs = (TextInput, NumberInput, EmailInput, URLInput, PasswordInput, HiddenInput, DefaultDateInput, DateInput, DateTimeInput, TimeInput)
        select_inputs = (Select, SelectMultiple, NullBooleanSelect)
        for fname, f in self.fields.items():
            input_type = f.widget.__class__
            model_name = str(self.Meta.model).split('.')[-1].strip("'>").lower()
            if input_type in text_inputs:
                f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
            if input_type in select_inputs:
                f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
            if input_type == Textarea:
                f.widget.attrs['class'] = 'block p-2.5 w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500'
                f.widget.attrs['placeholder'] = 'Comments are often useful...'
            if input_type == CheckboxInput:
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
                f.widget.attrs['class'] = 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
                

class RiskAnalysisCreateForm(StyledModelForm):
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'is_draft', 'rating_matrix', 'comments']

class MeasureCreateForm(StyledModelForm):
    class Meta:
        model = Mitigation
        fields = '__all__'
        labels = {
            'risk_instance': 'Risk Scenario',
            'solution': 'Security Function',
        }
        widgets = {
            'eta': DefaultDateInput()
        }

        
class SecurityFunctionCreateForm(StyledModelForm):
    class Meta:
        model = Solution
        fields = '__all__'

class ThreatCreateForm(StyledModelForm):
    class Meta:
        model = ParentRisk
        fields = '__all__'

class UserCreateForm(StyledModelForm):
    class Meta:
        model = User
        fields = '__all__'

class RiskAnalysisUpdateForm(StyledModelForm):
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'version', 'is_draft', 'rating_matrix', 'comments']

class RiskInstanceCreateForm(StyledModelForm):
    class Meta:
        model = RiskInstance
        exclude = ['analysis', 'residual_level', 'current_level']

class RiskInstanceUpdateForm(StyledModelForm):
    class Meta:
        model = RiskInstance
        fields = '__all__'
        exclude = ['current_level', 'residual_level']

class MitigationUpdateForm(StyledModelForm):
    class Meta:
        model = Mitigation
        exclude = ['risk_instance']

class ProjectsGroupUpdateForm(StyledModelForm):
    class Meta:
        model = ProjectsGroup
        fields = '__all__'

class ProjectUpdateForm(StyledModelForm):
    class Meta:
        model = Project
        fields = '__all__'

class SecurityFunctionUpdateForm(StyledModelForm):
    class Meta:
        model = Solution
        fields = '__all__'

class ThreatUpdateForm(StyledModelForm):
    class Meta:
        model = ParentRisk
        fields = '__all__'

class RiskAcceptanceCreateUpdateForm(StyledModelForm):
    class Meta:
        model = RiskAcceptance
        fields = '__all__'
        widgets = {
            'expiry_date': DefaultDateInput()
        }

class ProjectForm(StyledModelForm):
    class Meta:
        model = Project
        fields = '__all__'

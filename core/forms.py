from django.forms import CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import *
from django.utils.translation import gettext_lazy as _


class DefaultDateInput(DateInput):
    input_type = 'date'


class StyledModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(__class__, self).__init__(*args, **kwargs)
        text_inputs = (TextInput, NumberInput, EmailInput, URLInput, PasswordInput, HiddenInput, DefaultDateInput, DateInput, DateTimeInput, TimeInput)
        select_inputs = (Select, SelectMultiple, NullBooleanSelect)
        for fname, f in self.fields.items():
            input_type = f.widget.__class__
            if self.Meta.model:
                model_name = str(self.Meta.model).split('.')[-1].strip("'>").lower()
            if input_type in text_inputs:
                f.widget.attrs['id'] = f'id_{model_name}_{fname}' if model_name else f'id_{fname}'
                f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            if input_type in select_inputs:
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
                f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50'
            if input_type == Textarea:
                f.widget.attrs['class'] = 'block p-2.5 w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500'
            if input_type == CheckboxInput:
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
                f.widget.attrs['class'] = 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
            if input_type == DefaultDateInput:
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
                f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'


class LoginForm(AuthenticationForm):
    username = forms.CharField(label=_("Email"), widget=forms.TextInput(attrs={'class': 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput(attrs={'class': 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}))

class RiskAnalysisCreateForm(StyledModelForm):
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'is_draft', 'rating_matrix', 'comments']
        
class RiskAnalysisCreateFormInherited(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].widget.attrs['select_disabled'] = True
        
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'is_draft', 'rating_matrix', 'comments']


class RiskAnalysisUpdateForm(StyledModelForm):
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'version', 'is_draft', 'rating_matrix', 'comments']


class SecurityMeasureCreateForm(StyledModelForm):
    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        widgets = {
            'eta': DefaultDateInput()
        }

class SecurityMeasureCreateFormInherited(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].widget.attrs['select_disabled'] = True

    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        widgets = {
            'eta': DefaultDateInput()
        }


class SecurityMeasureUpdateForm(StyledModelForm):
    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        widgets = {
            'eta': DefaultDateInput(format='%Y-%m-%d')
        }


class RiskScenarioCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['analysis'].widget.attrs['select_disabled'] = True
    class Meta:
        model = RiskScenario
        fields = ['analysis', 'threat', 'name', 'scenario']


class RiskScenarioUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['current_proba'].widget.attrs['onchange'] = 'refresh();'
        self.fields['current_impact'].widget.attrs['onchange'] = 'refresh();'
        self.fields['residual_proba'].widget.attrs['onchange'] = 'refresh();'
        self.fields['residual_impact'].widget.attrs['onchange'] = 'refresh();'

    class Meta:
        model = RiskScenario
        fields = '__all__'
        exclude = ['current_level', 'residual_level']


class RiskScenarioModalUpdateForm(StyledModelForm):
    class Meta:
        model = RiskScenario
        fields = '__all__'


class RiskAcceptanceCreateUpdateForm(StyledModelForm):
    class Meta:
        model = RiskAcceptance
        fields = '__all__'
        widgets = {
            'expiry_date': DefaultDateInput(format='%Y-%m-%d')
        }
        labels = {'risk_scenario': _('Risk scenario')}
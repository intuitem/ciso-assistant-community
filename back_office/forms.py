from django.forms import CharField, CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, widgets
from django.contrib.auth.models import User
from .models import RoleAssignment, UserGroup, Role
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from core.models import Analysis, SecurityMeasure, RiskAcceptance, RiskScenario
from general.models import Asset, Threat, Project, Folder, SecurityFunction
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
                f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            if input_type == Textarea:
                f.widget.attrs['class'] = 'block p-2.5 w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500'
            if input_type == CheckboxInput:
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
                f.widget.attrs['class'] = 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
            if input_type == DefaultDateInput:
                f.widget.attrs['id'] = f'id_{model_name}_{fname}'
                f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
                

class RiskAnalysisCreateForm(StyledModelForm):
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'is_draft', 'rating_matrix', 'comments']

class SecurityMeasureCreateForm(StyledModelForm):
    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        labels = {
            'risk_scenario': _('Risk scenario'),
            'security_function': _('Security function'),
        }
        widgets = {
            'eta': DefaultDateInput()
        }

        
class SecurityFunctionCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(SecurityFunctionCreateForm, self).__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type="GL")

    class Meta:
        model = SecurityFunction
        fields = '__all__'

class ThreatCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(ThreatCreateForm, self).__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type="GL")

    class Meta:
        model = Threat
        fields = '__all__'

class UserCreateForm(UserCreationForm, StyledModelForm):
    pass

class UserUpdateForm(UserChangeForm, StyledModelForm):
    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        password = self.fields.get('password')
        self.fields['password'].help_text=_(
            'Raw passwords are not stored, so there is no way to see this '
            'user’s password, but you can change the password using '
            '<a class="help_text-link" href="{}">this form</a>.'
        )
        self.fields['password'].widget.attrs['class'] = 'text-sm -mb-1 password_update'
        self.fields['is_active'].widget.attrs['class'] += ' -mt-1'
        if password:
            password.help_text = password.help_text.format(
                reverse('admin-password-change', 
                kwargs={'pk': user.pk}
            ))

    field_order = ['username', 'password', 'first_name', 'last_name', 'email', 'is_active']

    class Meta:
        model = User
        exclude = ['last_login', 'is_superuser', 'is_staff', 'date_joined', 'user_permissions']

class AdminPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        for fname, f in self.fields.items():
            f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            print('FNAME:', fname)
        self.fields.get('password1').widget.attrs['id'] = 'password1'
        self.fields.get('password2').widget.attrs['id'] = 'password2'

class GroupCreateForm(StyledModelForm):
    class Meta:
        model = UserGroup
        exclude = ['permissions', 'builtin']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class GroupUpdateForm(StyledModelForm):
    class Meta:
        model = UserGroup
        exclude = ['permissions', 'builtin']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class RoleAssignmentUpdateForm(StyledModelForm):
    class Meta:
        model = Role
        fields = ['permissions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].widget.attrs['class'] += ' h-96'


class RiskAnalysisUpdateForm(StyledModelForm):
    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'version', 'is_draft', 'rating_matrix', 'comments']

class RiskScenarioCreateForm(StyledModelForm):
    class Meta:
        model = RiskScenario
        exclude = ['analysis', 'residual_level', 'current_level']

class RiskScenarioCreateForm(StyledModelForm):
    class Meta:
        model = RiskScenario
        fields = ['analysis', 'threat', 'title', 'scenario']

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
        exclude = ['current_level', 'residual_level', 'assets']

class RiskScenarioModalUpdateForm(StyledModelForm):
    class Meta:
        model = RiskScenario
        fields = '__all__'

class SecurityMeasureUpdateForm(StyledModelForm):
    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        widgets = {
            'eta': DefaultDateInput(format='%Y-%m-%d')
        }

class FolderUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(FolderUpdateForm, self).__init__(*args, **kwargs)
        self.fields['parent_folder'].queryset = Folder.objects.filter(content_type="GL")

    class Meta:
        model = Folder
        exclude = ['content_type', 'builtin']


class ProjectUpdateForm(StyledModelForm):

    class Meta:
        model = Project
        fields = '__all__'


class SecurityFunctionUpdateForm(StyledModelForm):
    class Meta:
        model = SecurityFunction
        fields = '__all__'

class ThreatUpdateForm(StyledModelForm):

    class Meta:
        model = Threat
        fields = '__all__'

class RiskAcceptanceCreateUpdateForm(StyledModelForm):
    class Meta:
        model = RiskAcceptance
        fields = '__all__'
        widgets = {
            'expiry_date': DefaultDateInput(format='%Y-%m-%d')
        }
        labels = {'risk_scenario': _('Risk scenario')}

class ProjectForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type="DO")

    class Meta:
        model = Project
        fields = '__all__'
        labels = {'domain': _('Domain')}

class AssetForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type="GL")

    class Meta:
        model = Asset
        fields = '__all__'

class RoleAssignmentForm(StyledModelForm):
    class Meta:
        model = RoleAssignment
        exclude = ['builtin']
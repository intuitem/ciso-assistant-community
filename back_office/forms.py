from django.forms import CharField, CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, widgets
from django.contrib.auth.models import User
from .models import UserGroup, Role
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from core.models import Analysis, Mitigation, RiskAcceptance, RiskInstance
from general.models import Asset, ParentRisk, Project, Folder, Solution
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

class MeasureCreateForm(StyledModelForm):
    class Meta:
        model = Mitigation
        fields = '__all__'
        labels = {
            'risk_instance': _('Risk scenario'),
            'solution': _('Security function'),
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

    field_order = ['username', 'password', 'first_name', 'last_name', 'email', 'is_active', 'groups']

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
        exclude = ['permissions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class GroupUpdateForm(StyledModelForm):
    class Meta:
        model = UserGroup
        exclude = ['permissions']

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

class RiskInstanceCreateForm(StyledModelForm):
    class Meta:
        model = RiskInstance
        exclude = ['analysis', 'residual_level', 'current_level']

class RiskScenarioCreateForm(StyledModelForm):
    class Meta:
        model = RiskInstance
        fields = ['analysis', 'parent_risk', 'title', 'scenario']

class RiskInstanceUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['current_proba'].widget.attrs['onchange'] = 'refresh();'
        self.fields['current_impact'].widget.attrs['onchange'] = 'refresh();'
        self.fields['residual_proba'].widget.attrs['onchange'] = 'refresh();'
        self.fields['residual_impact'].widget.attrs['onchange'] = 'refresh();'

    class Meta:
        model = RiskInstance
        fields = '__all__'
        exclude = ['current_level', 'residual_level', 'assets']

class MitigationUpdateForm(StyledModelForm):
    class Meta:
        model = Mitigation
        exclude = ['risk_instance']
        widgets = {
            'eta': DefaultDateInput(format='%Y-%m-%d')
        }

class FolderUpdateForm(StyledModelForm):
    class Meta:
        model = Folder
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
            'expiry_date': DefaultDateInput(format='%Y-%m-%d')
        }
        labels = {'risk_instance': _('Risk scenario')}

class ProjectForm(StyledModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        labels = {'domain': _('Domain')}

class AssetForm(StyledModelForm):
    class Meta:
        model = Asset
        fields = '__all__'

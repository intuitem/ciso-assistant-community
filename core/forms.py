from typing import Optional, Sequence
from django.forms import CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, CheckboxSelectMultiple
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django import forms
from .models import *
from iam.models import RoleAssignment
from django.utils.translation import gettext_lazy as _
from django.utils.html import escape
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from asf_rm.settings import RECAPTCHA_PUBLIC_KEY

if RECAPTCHA_PUBLIC_KEY:
    from captcha.fields import ReCaptchaField
    from captcha.widgets import ReCaptchaV2Checkbox

User = get_user_model()

class LinkCleanMixin:
    """
    Prevent code injection in link field
    """
    def clean_link(self):
        """
        Method to check if a link is valid
        """
        link = self.cleaned_data.get('link')
        if link:
            link = escape(link)
            if not link.startswith(('https://', 'ftps://')):
                raise ValidationError(_('Invalid link'))
        return link

class SearchableCheckboxSelectMultiple(CheckboxSelectMultiple):
    """
    A searchable checkbox select multiple widget.

    Widget attributes (in addition to the standard ones):
        - wrapper_class: class for the wrapper div
        - searchbar_class: class for the searchbar
    """
    template_name = 'forms/widgets/select_multiple.html'


class SearchableSelect(Select):
    template_name = 'forms/widgets/searchable_select.html'
    option_template_name = 'forms/widgets/select_option.html'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.id = f'searchable-select-{id(self)}'

class DefaultDateInput(DateInput):
    input_type = 'date'


class StyledModelForm(ModelForm):
    def default_if_one(self, field_name):
        field=self.fields[field_name]
        if not hasattr(field, '_queryset'):
            return
        if field._queryset and len(field._queryset) == 1:
            field.widget.attrs['disabled'] = True
            field.widget.attrs['class'] += ' disabled:opacity-50'
            field.initial = field.queryset[0]

    def default_if_one_all(self):
        for fname, f in self.fields.items():
            self.default_if_one(fname)

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
            if input_type == Select:
                self.default_if_one(fname)

class LoginForm(AuthenticationForm):
    username = forms.CharField(label=_("Email"), required=False, widget=forms.TextInput(attrs={'class': 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}))
    password = forms.CharField(label=_("Password"), required=False, widget=forms.PasswordInput(attrs={'class': 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}))

    def clean(self):
        username = self.cleaned_data.get('username').lower()
        password = self.cleaned_data.get('password')
        passkey = self.request.POST.get('passkeys')
        if (username and password) or passkey:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)
        else:
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
                params={'username': self.username_field.verbose_name},
            )
        return self.cleaned_data

class ResetForm(forms.Form):
    email = forms.EmailField(label=_("Email"), widget=forms.TextInput(attrs={'class': 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}))
    if RECAPTCHA_PUBLIC_KEY:
        captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)


class ResetConfirmForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):  
        style = 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'
        super(__class__, self).__init__(*args, **kwargs)
        for password in self.fields.items():
            password[1].widget.attrs['class'] = style

class FirstConnexionConfirmForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):  
        style = 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'
        super(__class__, self).__init__(*args, **kwargs)
        for password in self.fields.items():
            password[1].widget.attrs['class'] = style
        self.fields['terms_service'].widget.attrs['class'] = 'ml-2 rounded border-gray-300 shadow-sm focus:border-indigo-600 focus:ring focus:ring-indigo-500 focus:ring-opacity-50 text-indigo-500'
        self.fields['terms_service'].widget.attrs['id'] = 'terms_service'
    
    terms_service = forms.BooleanField(label=_("terms and conditions of use"))

class RiskAnalysisCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating_matrix'].queryset = RiskMatrix.objects.filter(is_enabled=True)
        self.fields['rating_matrix'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['rating_matrix'].choices)
        self.fields['project'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['project'].choices)
        self.default_if_one_all()

    class Meta:
        model = Analysis
        fields = ['project', 'name', 'description', 'auditor', 'is_draft', 'rating_matrix', 'version']
        
class RiskAnalysisCreateFormInherited(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].widget.attrs['disabled'] = True
        self.fields['rating_matrix'].queryset = RiskMatrix.objects.filter(is_enabled=True)
        self.fields['rating_matrix'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['rating_matrix'].choices)
        self.default_if_one_all()
        
    class Meta:
        model = Analysis
        fields = ['project', 'name', 'description', 'auditor', 'is_draft', 'rating_matrix', 'version']


class RiskMatrixUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_if_one_all()

    class Meta:
        model = RiskMatrix
        fields = ['is_enabled']


class RiskAnalysisUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].widget.attrs['disabled'] = True
        self.fields['project'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['project'].choices)
        self.fields['auditor'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['auditor'].choices)

    class Meta:
        model = Analysis
        fields = ['project', 'auditor', 'name', 'description', 'version', 'is_draft']


class SecurityMeasureCreateForm(LinkCleanMixin, StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['folder'].queryset = Folder.objects.filter(id__in=RoleAssignment.get_accessible_folders(Folder.objects.get(content_type=Folder.ContentType.ROOT), user, Folder.ContentType.DOMAIN, codename="add_securitymeasure"))
        else:
            self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        self.fields['folder'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['folder'].choices)
        self.fields['security_function'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['security_function'].choices)

    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        widgets = {
            'eta': DefaultDateInput()
        }

class SecurityMeasureCreateFormInherited(LinkCleanMixin, StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        self.fields['folder'].widget.attrs['disabled'] = True
        self.fields['security_function'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['security_function'].choices)

    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        widgets = {
            'eta': DefaultDateInput()
        }


class SecurityMeasureUpdateForm(LinkCleanMixin, StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        self.fields['folder'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['folder'].choices)
        self.fields['security_function'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['security_function'].choices)
    
    class Meta:
        model = SecurityMeasure
        fields = '__all__'
        widgets = {
            'eta': DefaultDateInput(format='%Y-%m-%d')
        }

class RiskScenarioCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['threat'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['threat'].choices)

    class Meta:
        model = RiskScenario
        fields = ['analysis', 'threat', 'name', 'description']


class RiskScenarioUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PROBA_CHOICES = [(-1, '--')] + list(zip(list(range(0, 10)), [x['name'] for x in self.instance.get_matrix()['probability']]))
        IMPACT_CHOICES = [(-1, '--')] + list(zip(list(range(0, 10)), [x['name'] for x in self.instance.get_matrix()['impact']]))
        self.fields['current_proba'].widget = Select(choices=PROBA_CHOICES, attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50',
            'onchange': 'refresh();'
        })
        self.fields['current_impact'].widget = Select(choices=IMPACT_CHOICES, attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50',
            'onchange': 'refresh();'
        })
        self.fields['residual_proba'].widget = Select(choices=PROBA_CHOICES, attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50',
            'onchange': 'refresh();'
        })
        self.fields['residual_impact'].widget = Select(choices=IMPACT_CHOICES, attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50',
            'onchange': 'refresh();'
        })
        self.fields['assets'].widget = SearchableCheckboxSelectMultiple(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 overflow-y-scroll h-80'},
                   choices=self.fields['assets'].choices)
        self.fields['threat'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['threat'].choices)
        self.fields['analysis'].widget = SearchableSelect(attrs={'class': 'text-sm rounded w-64',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll',
                   'id': 'analysis_select'},
                   choices=self.fields['analysis'].choices)

    class Meta:
        model = RiskScenario
        fields = '__all__'
        exclude = ['current_level', 'residual_level']


class SecurityMeasureSelectForm(StyledModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['security_measures'].widget = SearchableCheckboxSelectMultiple(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 max-h-56 overflow-y-scroll'},
                   choices=self.fields['security_measures'].choices)

    class Meta:
        model = RiskScenario
        fields = ['security_measures']


class RiskScenarioModalUpdateForm(StyledModelForm):
    class Meta:
        model = RiskScenario
        fields = '__all__'


class RiskAcceptanceCreateUpdateForm(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['risk_scenarios'].widget = SearchableCheckboxSelectMultiple(attrs={'id': 'id_riskscenarios_select', 'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 max-h-56 overflow-y-scroll'},
                   choices=self.fields['risk_scenarios'].choices)
        validators_id = []
        for candidate in User.objects.all():
            if RoleAssignment.has_permission(candidate, 'validate_riskacceptance'):
                validators_id.append(candidate.id)
        self.fields['validator'].queryset = User.objects.filter(id__in=validators_id)
        if user:
            self.fields['folder'].queryset = Folder.objects.filter(id__in=RoleAssignment.get_accessible_folders(Folder.objects.get(content_type=Folder.ContentType.ROOT), user, None, codename="add_riskacceptance"))
        # else:
        #     self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        # Else statement causes a problem because during submition for global folder
        # Folder.objects.filter(content_type=Folder.ContentType.DOMAIN) doesn't content global so an error occured

    class Meta:
        model = RiskAcceptance
        fields = '__all__'
        widgets = {
            'expiry_date': DefaultDateInput(format='%Y-%m-%d'),
        }
        labels = {'risk_scenario': _('Risk scenario')}
        exclude = ['state', 'accepted_date', 'rejected_date', 'revoked_date']
    
    def clean(self):
        cleaned_data = super().clean()
        risk_scenarios = cleaned_data.get('risk_scenarios')
        folder = cleaned_data.get('folder')
        validator = cleaned_data.get('validator')

        folders = folder.sub_folders()
        folders.append(folder)
        if validator:
            if not RoleAssignment.is_access_allowed(validator, Permission.objects.get(codename='validate_riskacceptance'), folder):
                raise ValidationError(_("This  validator cannot be assigned for this domain"))
        if risk_scenarios:
            for obj in risk_scenarios:
                if obj.analysis.project.folder not in folders:
                    raise ValidationError(_("Checked risk scenarios must be part of the selected domain"))


class ProjectForm(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):   
        super(ProjectForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['folder'].queryset = Folder.objects.filter(id__in=RoleAssignment.get_accessible_folders(Folder.objects.get(content_type=Folder.ContentType.ROOT), user, Folder.ContentType.DOMAIN, codename="add_project"))
        else:
            self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        self.fields['folder'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                choices=self.fields['folder'].choices)


    class Meta:
        model = Project
        fields = '__all__'
        labels = {'folder': _('Domain')}

class ProjectFormInherited(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(ProjectFormInherited, self).__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        self.fields['folder'].widget.attrs['disabled'] = True

    class Meta:
        model = Project
        fields = '__all__'
        labels = {'folder': _('Domain')}


class ThreatCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(ThreatCreateForm, self).__init__(*args, **kwargs)
        

    class Meta:
        model = Threat
        fields = '__all__'
        exclude = ['is_published', 'folder']


class ThreatUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(ThreatUpdateForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Threat
        fields = '__all__'
        exclude = ['is_published', 'folder']


class AssetForm(StyledModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        self.fields['parent_assets'].widget = SearchableCheckboxSelectMultiple(attrs={'class': 'text-sm rounded',
                     'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3',
                        'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 max-h-56 overflow-y-scroll'},
                        choices=self.fields['parent_assets'].choices)
        viewable_assets = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), user, Asset)[0] if user else Asset.objects.none()
        self.fields['parent_assets'].queryset = Asset.objects.filter(id__in=viewable_assets
            ).exclude(id=self.instance.id) if self.instance else Asset.objects.filter(id__in=viewable_assets)

    def clean(self):
        """ check the AssetForm values before submission to the model. This is required as we used manytomany """
        cleaned_data = super().clean()
        parent_assets = cleaned_data.get('parent_assets')
        asset_type = cleaned_data.get('type')
        if asset_type == Asset.Type.PRIMARY and parent_assets.exists():
            raise ValidationError(_('A primary asset cannot have parent assets.'))
        # if we are in an update form, let's check there are no cycles
        if self.instance:
            for parent in parent_assets.all():
                if self.instance in parent.ancestors_plus_self():
                    raise ValidationError(_('Cycles are not allowed.'))
        return cleaned_data

    class Meta:
        model = Asset
        exclude = ['is_published', 'folder']


class SecurityFunctionCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(SecurityFunctionCreateForm, self).__init__(*args, **kwargs)

    class Meta:
        model = SecurityFunction
        fields = '__all__'
        exclude = ['is_published', 'folder']


class SecurityFunctionUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(SecurityFunctionUpdateForm, self).__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.ROOT)
        self.fields['folder'].disabled = True
    class Meta:
        model = SecurityFunction
        fields = '__all__'
        exclude = ['is_published', 'folder']

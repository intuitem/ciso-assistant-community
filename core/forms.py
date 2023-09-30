from typing import Any, Dict, Optional
from django.forms import CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, CheckboxSelectMultiple, ValidationError, FileInput
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django import forms
from .models import *
from iam.models import RoleAssignment
from django.utils.translation import gettext_lazy as _
from django.utils.html import escape
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from ciso_assistant.settings import RECAPTCHA_PUBLIC_KEY
from django.db.models import Case, When, Value, IntegerField

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
    recommended_security_measures = None

    def __init__(self, recommended_security_measures=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.recommended_security_measures = recommended_security_measures
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.recommended_security_measures:
            context["recommended_security_measures"] = self.recommended_security_measures
        return context



class SearchableSelect(Select):
    template_name = 'forms/widgets/searchable_select.html'
    option_template_name = 'forms/widgets/select_option.html'
    recommended_security_functions = None

    def __init__(self, recommended_security_functions=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.recommended_security_functions = recommended_security_functions
        self.id = f'searchable-select-{id(self)}'
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.recommended_security_functions:
            context["recommended_security_functions"] = self.recommended_security_functions
        return context

    

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
                f.widget.attrs['autocomplete'] = 'off' # workaround for Firefox behavior: https://stackoverflow.com/questions/4831848/firefox-ignores-option-selected-selected
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
                print("Authentication failed")
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)
                print("Authentication succeeded for ", self.user_cache)
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

class SecurityMeasureCreateForm(LinkCleanMixin, StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['security_function'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['security_function'].choices)
        self.fields['folder'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['folder'].choices)

    class Meta:
        model = SecurityMeasure
        exclude = ['locale_data']
        widgets = {
            'eta': DefaultDateInput()
        }


class SecurityMeasureCreateFormInherited(LinkCleanMixin, StyledModelForm):
    
    add_evidence = forms.BooleanField(help_text=_("Check this if you want to attach an evidence right after"))

    def __init__(self, recommended_security_functions=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if recommended_security_functions:
            custom_ordering = Case(
                When(id__in=recommended_security_functions, then=Value(0)),
                default=Value(1),
                output_field=IntegerField()
            )
            self.fields['security_function'].queryset = SecurityFunction.objects.all().order_by(custom_ordering)
        self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        self.fields['folder'].widget.attrs['disabled'] = True
        self.fields['security_function'].widget = SearchableSelect(recommended_security_functions.values_list('id', flat=True), attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
                   choices=self.fields['security_function'].choices)

    class Meta:
        model = SecurityMeasure
        exclude = ['locale_data']
        widgets = {
            'eta': DefaultDateInput()
        }


class SecurityMeasureUpdateForm(LinkCleanMixin, StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        exclude = ['locale_data']
        widgets = {
            'eta': DefaultDateInput(format='%Y-%m-%d')
        }

class ProjectForm(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):   
        super().__init__(*args, **kwargs)
        if user:
            self.fields['folder'].queryset = Folder.objects.filter(id__in=RoleAssignment.get_accessible_folders(Folder.get_root_folder(), user, Folder.ContentType.DOMAIN, codename="add_project"))
        else:
            self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        # TODO: find why with SearchableSelect ValidationError on empty <select> is bypassed by ValueError on empty UUID when no folder is selected
        # self.fields['folder'].widget = SearchableSelect(attrs={'class': 'text-sm rounded',
        #         'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
        #         'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'},
        #         choices=self.fields['folder'].choices)


    class Meta:
        model = Project
        exclude = ['locale_data']
        labels = {'folder': _('Domain')}

class ProjectFormInherited(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN)
        self.fields['folder'].widget.attrs['disabled'] = True

    class Meta:
        model = Project
        exclude = ['locale_data']
        labels = {'folder': _('Domain')}


class ThreatCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

    class Meta:
        model = Threat
        exclude = ['is_published', 'folder', 'locale_data', 'urn']


class ThreatUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Threat
        exclude = ['is_published', 'folder', 'locale_data', 'urn']


class SecurityFunctionCreateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = SecurityFunction
        exclude = ['is_published', 'folder', 'locale_data', 'urn']


class SecurityFunctionUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    class Meta:
        model = SecurityFunction
        exclude = ['is_published', 'folder', 'locale_data', 'urn']


class AssessmentCreateForm(StyledModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Assessment
        fields = ['project', 'framework', 'name', 'description']


class AssessmentUpdateForm(StyledModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Assessment
        fields = ['name', 'description', 'version', 'is_draft', 'is_obsolete']


class FrameworkForm(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Framework
        exclude = ['locale_data', 'urn']


class RequirementForm(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Requirement
        exclude = ['locale_data']


class RequirementFormInherited(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['framework'].queryset = Framework.objects.all()
        self.fields['framework'].widget.attrs['disabled'] = True
        self.fields['folder'].queryset = Folder.objects.all()
        self.fields['folder'].widget.attrs['disabled'] = True

    class Meta:
        model = Requirement
        exclude = ['locale_data']
        labels = {'folder': _('Domain')}


class EvidenceForm(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Evidence
        widgets = {'attachment': FileInput(attrs={'accept': """application/pdf, text/plain
                                                  application/msword, image/png, image/jpeg, image/jpg, 
                                                  application/vnd.openxmlformats-officedocument.wordprocessingml.document,
                                                  text/csv, application/vnd.ms-excel,
                                                  application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"""})}
        exclude = ['folder', 'locale_data']


class EvidenceUpdateForm(EvidenceForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Evidence
        widgets = {'attachment': FileInput(attrs={'accept': """application/pdf, text/plain
                                                  application/msword, image/png, image/jpeg, image/jpg, 
                                                  application/vnd.openxmlformats-officedocument.wordprocessingml.document,
                                                  text/csv, application/vnd.ms-excel,
                                                  application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"""})}
        exclude = ['folder', 'locale_data', 'measure']


class EvidenceFormInherited(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['measure'].queryset = SecurityMeasure.objects.all()
        self.fields['measure'].widget.attrs['disabled'] = True

    class Meta:
        model = Evidence
        widgets = {'attachment': FileInput(attrs={'accept': """application/pdf, text/plain
                                                  application/msword, image/png, image/jpeg, image/jpg, 
                                                  application/vnd.openxmlformats-officedocument.wordprocessingml.document,
                                                  text/csv, application/vnd.ms-excel,
                                                  application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"""})}
        exclude = ['folder', 'locale_data']


class RequirementAssessmentForm(StyledModelForm):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = RequirementAssessment
        fields = ["status", "comment"]
        widgets = {
            'comment': forms.Textarea(attrs={'rows': '5'})
        }


class SecurityMeasureSelectForm(StyledModelForm):

    def __init__(self, recommended_security_measures=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['security_measures'].widget = SearchableCheckboxSelectMultiple(recommended_security_measures.values_list("id", flat=True), attrs={'class': 'text-sm rounded',
                   'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3',
                   'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 max-h-56 overflow-y-scroll'},
                   choices=self.fields['security_measures'].choices)

    class Meta:
        model = RequirementAssessment
        fields = ['security_measures']

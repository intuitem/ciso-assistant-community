from django.forms import CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput
from .models import *
from django.contrib.auth.forms import UserChangeForm, AdminPasswordChangeForm
from django.urls import reverse
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


class FolderUpdateForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super(FolderUpdateForm, self).__init__(*args, **kwargs)
        self.fields['parent_folder'].queryset = Folder.objects.filter(content_type="GL")

    class Meta:
        model = Folder
        exclude = ['content_type', 'builtin']


class UsernameField(forms.CharField):
    def to_python(self, value):
        return unicodedata.normalize('NFKC', super().to_python(value))

    def widget_attrs(self, widget):
        return {
            **super().widget_attrs(widget),
            'autocapitalize': 'none',
            'autocomplete': 'username',
        }


class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'password_mismatch': _('The two password fields didn’t match.'),
    }
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        field_classes = {'username': UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._meta.model.USERNAME_FIELD in self.fields:
            self.fields[self._meta.model.USERNAME_FIELD].widget.attrs['autofocus'] = True

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get('password2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password2', error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserCreateForm(UserCreationForm, StyledModelForm):
    pass


class UserUpdateForm(UserChangeForm, StyledModelForm):
    def __init__(self, *args, user,**kwargs):
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


class MeUpdateForm(UserChangeForm, StyledModelForm):
    def __init__(self, *args, user,**kwargs):
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

    field_order = ['username', 'password', 'first_name', 'last_name', 'is_active']

    class Meta:
        model = User
        exclude = ['last_login', 'is_superuser', 'is_staff', 'date_joined', 'user_permissions', 'user_groups']


class AdminPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        for fname, f in self.fields.items():
            f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            print('FNAME:', fname)
        self.fields.get('password1').widget.attrs['id'] = 'password1'
        self.fields.get('password2').widget.attrs['id'] = 'password2'

class UserGroupCreateForm(StyledModelForm):
    class Meta:
        model = UserGroup
        exclude = ['permissions', 'builtin']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class UserGroupUpdateForm(StyledModelForm):
    class Meta:
        model = UserGroup
        exclude = ['permissions', 'builtin']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class RoleAssignmentForm(StyledModelForm):
    class Meta:
        model = RoleAssignment
        exclude = ['builtin']


class RoleAssignmentUpdateForm(StyledModelForm):
    class Meta:
        model = Role
        fields = ['permissions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].widget.attrs['class'] += ' h-96'
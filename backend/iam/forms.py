""" this module contains forms related to iam app
"""
from django.forms import (
    CheckboxInput,
    DateInput,
    DateTimeInput,
    EmailInput,
    HiddenInput,
    ModelForm,
    NullBooleanSelect,
    NumberInput,
    PasswordInput,
    Select,
    SelectMultiple,
    TextInput,
    Textarea,
    TimeInput,
    URLInput,
    ValidationError,
)
from django.contrib.auth.forms import UserChangeForm, AdminPasswordChangeForm
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import password_validation
from django import forms
from .models import Folder, User, UserGroup, RoleAssignment, Role

from core.forms import SearchableCheckboxSelectMultiple


class DefaultDateInput(DateInput):
    """default date for input"""

    input_type = "date"


class StyledModelForm(ModelForm):
    """a nice ModelForm"""

    def __init__(self, *args, **kwargs):
        # pragma pylint: disable=no-member
        super(__class__, self).__init__(*args, **kwargs)
        text_inputs = (
            TextInput,
            NumberInput,
            EmailInput,
            URLInput,
            PasswordInput,
            HiddenInput,
            DefaultDateInput,
            DateInput,
            DateTimeInput,
            TimeInput,
        )
        select_inputs = (Select, SelectMultiple, NullBooleanSelect)
        for fname, f in self.fields.items():
            input_type = f.widget.__class__
            if self.Meta.model:
                model_name = str(self.Meta.model).split(".")[-1].strip("'>").lower()
            if input_type in text_inputs:
                f.widget.attrs["id"] = (
                    f"id_{model_name}_{fname}" if model_name else f"id_{fname}"
                )
                f.widget.attrs[
                    "class"
                ] = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
            if input_type in select_inputs:
                f.widget.attrs["id"] = f"id_{model_name}_{fname}"
                f.widget.attrs[
                    "class"
                ] = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
            if input_type == Textarea:
                f.widget.attrs[
                    "class"
                ] = "block p-2.5 w-full text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500"
            if input_type == CheckboxInput:
                f.widget.attrs["id"] = f"id_{model_name}_{fname}"
                f.widget.attrs[
                    "class"
                ] = "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            if input_type == DefaultDateInput:
                f.widget.attrs["id"] = f"id_{model_name}_{fname}"
                f.widget.attrs[
                    "class"
                ] = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"


class FolderUpdateForm(StyledModelForm):
    """form to update a folder"""
    # pragma pylint: disable=no-member

    class Meta:
        """for Model"""

        model = Folder
        exclude = ["content_type", "builtin", "parent_folder"]


class UserCreationForm(forms.ModelForm):
    """A form for creating new users"""

    email = forms.EmailField(max_length=100)

    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        return email.lower()

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error("password2", error)

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserCreateForm(UserCreationForm, StyledModelForm):
    """form to create user"""

    pass


class UserUpdateForm(UserChangeForm, StyledModelForm):
    """form to update user"""

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        password = self.fields.get("password")
        self.fields["password"].help_text = _(
            "Raw passwords are not stored, so there is no way to see this "
            "user’s password, but you can change the password using "
            '<a class="help_text-link" href="{}">this form</a>.'
        )
        self.fields["password"].widget.attrs["class"] = "text-sm -mb-1 password_update"
        self.fields["is_active"].widget.attrs["class"] += " -mt-1"
        self.fields["user_groups"].widget = SearchableCheckboxSelectMultiple(
            choices=self.fields["user_groups"].choices,
            attrs={
                "class": "text-sm rounded",
                "searchbar_class": "[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3",
                "wrapper_class": "border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 max-h-56 overflow-y-scroll",
            },
        )
        if password:
            password.help_text = password.help_text.format(
                reverse("password-change", kwargs={"pk": user.pk})
            )

    field_order = ["email", "password", "first_name", "last_name", "is_active"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        return email.lower()

    class Meta:
        """for Model"""

        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "is_active",
            "user_groups",
        ]


class MyProfileUpdateForm(UserChangeForm, StyledModelForm):
    """form for logged user"""
    # TODO: not sure this section is useful, self user could be in user list with a mention "me"

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["readonly"] = True
        self.fields["email"].help_text = _(
            "To change your email address, please contact your administrator."
        )
        self.fields["password"].widget.attrs["class"] = "text-sm -mb-1 password_update"
        password = self.fields.get("password")
        self.fields["password"].help_text = _(
            "Raw passwords are not stored, so there is no way to see this "
            "user’s password, but you can change the password using "
            '<a class="help_text-link" href="{}">this form</a>.'
        )
        if password:
            password.help_text = password.help_text.format(
                reverse("password-change", kwargs={"pk": user.pk})
            )

    field_order = ["last_name", "first_name", "password", "email"]

    class Meta:
        model = User
        exclude = [
            "last_login",
            "is_superuser",
            "date_joined",
            "user_permissions",
            "user_groups",
            "is_active",
            "first_login",
        ]


class UserPasswordChangeForm(AdminPasswordChangeForm):
    """change user password form"""

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        for fname, f in self.fields.items():
            f.widget.attrs[
                "class"
            ] = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
            print("FNAME:", fname)
        self.fields.get("password1").widget.attrs["id"] = "password1"
        self.fields.get("password2").widget.attrs["id"] = "password2"


class UserGroupCreateForm(StyledModelForm):
    """form to create a user group"""

    class Meta:
        """for Model"""

        model = UserGroup
        exclude = ["permissions", "builtin"]


class UserGroupUpdateForm(StyledModelForm):
    """form to update a user group"""

    class Meta:
        """for Model"""

        model = UserGroup
        exclude = ["permissions", "builtin"]


class RoleAssignmentCreateForm(StyledModelForm):
    """form to create a RoleAssigment"""

    class Meta:
        """for Model"""

        model = RoleAssignment
        exclude = ["builtin"]


class RoleAssignmentUpdateForm(StyledModelForm):
    """form to update a RoleAssigment"""

    class Meta:
        """for Model"""

        model = Role
        fields = ["permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["permissions"].widget.attrs["class"] += " h-96"

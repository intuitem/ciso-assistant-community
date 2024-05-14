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
    CheckboxSelectMultiple,
    ValidationError,
)
from django.contrib.auth.forms import SetPasswordForm
from django import forms
from .models import *
from django.utils.translation import gettext_lazy as _
from django.utils.html import escape
from django.contrib.auth import get_user_model

User = get_user_model()


class LinkCleanMixin:
    """
    Prevent code injection in link field
    """

    def clean_link(self):
        """
        Method to check if a link is valid
        """
        link = self.cleaned_data.get("link")
        if link:
            link = escape(link)
            if not link.startswith(("https://", "ftps://")):
                raise ValidationError(_("Invalid link"))
        return link


class SearchableCheckboxSelectMultiple(CheckboxSelectMultiple):
    """
    A searchable checkbox select multiple widget.

    Widget attributes (in addition to the standard ones):
        - wrapper_class: class for the wrapper div
        - searchbar_class: class for the searchbar
    """

    template_name = "forms/widgets/select_multiple.html"
    recommended_applied_controls = None

    def __init__(self, recommended_applied_controls=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.recommended_applied_controls = recommended_applied_controls

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.recommended_applied_controls:
            context["recommended_applied_controls"] = self.recommended_applied_controls
        return context


class SearchableSelect(Select):
    template_name = "forms/widgets/searchable_select.html"
    option_template_name = "forms/widgets/select_option.html"
    recommended_reference_controls = None

    def __init__(self, recommended_reference_controls=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.recommended_reference_controls = recommended_reference_controls
        self.id = f"searchable-select-{id(self)}"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.recommended_reference_controls:
            context[
                "recommended_reference_controls"
            ] = self.recommended_reference_controls
        return context


class DefaultDateInput(DateInput):
    input_type = "date"


class StyledModelForm(ModelForm):
    def default_if_one(self, field_name):
        field = self.fields[field_name]
        if not hasattr(field, "_queryset"):
            return
        if field._queryset and len(field._queryset) == 1:
            field.widget.attrs["disabled"] = True
            field.widget.attrs["class"] += " disabled:opacity-50"
            field.initial = field.queryset[0]

    def default_if_one_all(self):
        for fname, f in self.fields.items():
            self.default_if_one(fname)

    def __init__(self, *args, **kwargs):
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
                    "autocomplete"
                ] = "off"  # workaround for Firefox behavior: https://stackoverflow.com/questions/4831848/firefox-ignores-option-selected-selected
                f.widget.attrs[
                    "class"
                ] = "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50"
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
            if input_type == Select:
                self.default_if_one(fname)


class ResetForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.TextInput(
            attrs={
                "class": "my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
            }
        ),
    )


class ResetConfirmForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        style = "my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
        super(__class__, self).__init__(*args, **kwargs)
        for password in self.fields.items():
            password[1].widget.attrs["class"] = style


class FirstConnexionConfirmForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        style = "my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
        super(__class__, self).__init__(*args, **kwargs)
        for password in self.fields.items():
            password[1].widget.attrs["class"] = style
        self.fields["terms_service"].widget.attrs[
            "class"
        ] = "ml-2 rounded border-gray-300 shadow-sm focus:border-indigo-600 focus:ring focus:ring-indigo-500 focus:ring-opacity-50 text-indigo-500"
        self.fields["terms_service"].widget.attrs["id"] = "terms_service"

    terms_service = forms.BooleanField(label=_("terms and conditions of use"))

from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils.translation import ugettext_lazy as _


class LoginForm(AuthenticationForm):
    username = forms.CharField(label=_("Username"), widget=forms.TextInput(attrs={'class': 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput(attrs={'class': 'my-2 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}))

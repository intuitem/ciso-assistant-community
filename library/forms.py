from django import forms
from django.utils.translation import gettext_lazy as _

class UploadFileForm(forms.Form):
    file = forms.FileField(required=True, label=_('Select a file'))

from django import forms
from django.utils.translation import gettext_lazy as _
from library.validators import validate_file_extension


class UploadFileForm(forms.Form):
    file = forms.FileField(
        required=True, label=_("Select a file"), validators=[validate_file_extension]
    )

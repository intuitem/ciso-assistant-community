from typing import Any, Dict
from django import forms
from django.utils.translation import gettext_lazy as _


class UploadFileForm(forms.Form):
    file = forms.FileField(required=True, label=_("Select a file"))

    def clean(self) -> Dict[str, Any]:
        cleaned_data = super().clean()
        file = cleaned_data.get("file")

        if file:
            if not file.name.endswith(".json"):
                self.add_error("file", _("File must be a JSON file."))

        return file

import os
import re
import unicodedata

from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import BaseValidator
import jsonschema


class JSONSchemaInstanceValidator(BaseValidator):
    """
    Validate a JSON schema instance
    """

    def __init__(self, schema):
        self.schema = schema

    def __call__(self, value):
        try:
            jsonschema.validate(value, self.schema)
        except jsonschema.exceptions.ValidationError as e:
            raise ValidationError(e.message)


def validate_file_size(value):
    """
    Check that file size doesn't exceed maximum authorized
    """
    filesize = value.size

    if filesize > int(settings.ATTACHMENT_MAX_SIZE_MB) * 1000000:
        raise ValidationError(
            f"The maximum file size that can be uploaded is {settings.ATTACHMENT_MAX_SIZE_MB} MB"
        )
    else:
        return value


ALLOWED_UPLOAD_EXTENSIONS = [
    "jpg",
    "jpeg",
    "png",
    "doc",
    "docx",
    "odt",
    "ppt",
    "pptx",
    "txt",
    "xls",
    "xlsx",
    "ods",
    "csv",
    "md",
    "pdf",
    "json",
    "yaml",
    "yml",
    "toml",
    "xml",
    "msg",
    "eml",
    "zip",
    "7z",
    "tar",
    "gz",
    "log",
    "svg",
    "mp4",
    "mov",
    "gif",
    "webp",
]


#: Path structure and Windows-reserved. Spaces, accents and case are kept.
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_file_name(name: str, max_length: int = 255) -> str:
    """Strip what is unsafe in a path, keep what makes the name readable.

    Over `max_length` the stem is cut, not the tail, so the extension survives.
    """
    # A Windows client sends a full path.
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    # Compose accents: one name, one byte sequence.
    name = unicodedata.normalize("NFC", name)
    name = _UNSAFE_FILENAME_CHARS.sub("-", name)
    name = "".join(c for c in name if c.isprintable())
    name = re.sub(r"\s+", " ", name)
    # A leading dot hides the file; Windows drops trailing dots and spaces.
    name = name.strip(" .")

    if len(name) > max_length:
        stem, extension = os.path.splitext(name)
        if len(extension) < max_length:
            name = stem[: max_length - len(extension)].rstrip(" .") + extension
        else:
            name = name[:max_length]
    return name


def _validate_file_extension_and_sanitize(value, allowed_extensions):
    stem, dot_extension = os.path.splitext(value.name)
    extension = dot_extension.lstrip(".").lower()

    if extension not in allowed_extensions:
        raise ValidationError(
            f"Unsupported file extension '.{extension}'. Allowed extensions: {', '.join(allowed_extensions)}"
        )
    if len(value.name) > 256:
        raise ValidationError("File name is too long")

    value.name = (sanitize_file_name(stem) or "file") + "." + extension
    return value


def validate_file_name(value):
    """
    Check file extension against the general upload allowlist and sanitize its name.
    """
    return _validate_file_extension_and_sanitize(value, ALLOWED_UPLOAD_EXTENSIONS)


def validate_html_template_file_name(value):
    """
    Filename check for HTML layout templates (server-side WeasyPrint templates,
    rendered by the platform and never served as attachments). `.html` is allowed
    here even though it is excluded from the general upload allowlist.
    """
    return _validate_file_extension_and_sanitize(value, ["html"])

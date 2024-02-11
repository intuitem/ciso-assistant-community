from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.text import get_valid_filename, slugify


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


def validate_file_name(value):
    """
    Check file extension and sanitize its name
    """
    allowed_extensions = [
        "jpg",
        "jpeg",
        "png",
        "docx",
        "txt",
        "xls",
        "xlsx",
        "csv",
        "pdf",
    ]
    parts = value.name.split(".")
    extension = parts[-1]

    if extension in allowed_extensions:
        if len(value.name) > 256:
            raise ValidationError("File name is too long")
        value.name = (
            slugify(get_valid_filename(value.name.replace(extension, "")))
            + "."
            + extension
        )
        return value
    else:
        raise ValidationError("An error occured with file extension")

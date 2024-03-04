from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


def validate_object(required_fields, fields):
    """
    Checks if the given object has all required fields

    Args:
        required_fields: list of required fields
        fields: object to check

    Returns:
        valid: True if the object has all required fields, False otherwise
    """
    for field in required_fields:
        if not fields.get(field):
            raise ValidationError(f"Missing required field: {field}")
    return True


def validate_file_extension(file):
    """
    Checks if the given file has a valid extension, raises a ValidationError if
    the extension is not valid.

    Valid extensions are: .json

    Args:
        file: file to check
    """
    allowed_extensions = ["yaml", "yml"]
    validator = FileExtensionValidator(allowed_extensions)
    validator(file)


def validate_threat(threat):
    """
    Checks if the given threat is valid

    Args:
        threat: threat to check

    Returns:
        valid: True if the threat is valid, False otherwise
    """
    pass


def validate_reference_control(reference_control):
    """
    Checks if the given reference control is valid

    Args:
        reference_control: reference control to check

    Returns:
        valid: True if the reference control is valid, False otherwise
    """
    pass


def validate_library(library):
    """
    Checks if the given library is valid

    Args:
        library: library to check

    Returns:
        valid: True if the library is valid, False otherwise
    """
    pass

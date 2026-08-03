from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import BaseValidator
from django.utils.text import get_valid_filename, slugify
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


# Magic-byte signatures of native executable / shared-object formats. An
# uploaded attachment must never be one of these, whatever its extension: a
# renamed executable (e.g. an ELF stored as ``.zip``) can be loaded as native
# code by the backend (SQLite ``load_extension``, dlopen, …). None of these
# signatures overlap with legitimate allowed types (docx/xlsx/zip start with
# ``PK``, PDF with ``%PDF``, OLE doc with ``\xd0\xcf\x11\xe0``, gzip ``\x1f\x8b``).
_EXECUTABLE_MAGIC = (
    b"\x7fELF",  # ELF (Linux/Unix)
    b"MZ",  # DOS/PE (Windows .exe/.dll)
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit big-endian
    b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit big-endian
    b"\xce\xfa\xed\xfe",  # Mach-O 32-bit little-endian
    b"\xcf\xfa\xed\xfe",  # Mach-O 64-bit little-endian
    b"\xca\xfe\xba\xbe",  # Mach-O universal / fat binary (also Java class)
    b"\xbe\xba\xfe\xca",  # Mach-O universal, byte-swapped
)


def reject_executable_content(value):
    """
    Reject uploads whose leading bytes match a native executable / shared-object
    signature, regardless of the declared extension. Defense against native code
    delivery (e.g. an ELF renamed to an allowed extension and later dlopen'd).
    """
    f = getattr(value, "file", value)
    try:
        pos = f.tell()
    except AttributeError, OSError:
        pos = None
    try:
        f.seek(0)
        header = f.read(8)
    finally:
        if pos is not None:
            f.seek(pos)
        else:
            try:
                f.seek(0)
            except AttributeError, OSError:
                pass

    if isinstance(header, str):
        header = header.encode("latin-1", "ignore")
    if any(header.startswith(sig) for sig in _EXECUTABLE_MAGIC):
        raise ValidationError("Executable content is not allowed as an attachment.")
    return value


def _validate_file_extension_and_sanitize(value, allowed_extensions):
    parts = value.name.split(".")
    extension = parts[-1].lower()

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
        raise ValidationError(
            f"Unsupported file extension '.{extension}'. Allowed extensions: {', '.join(allowed_extensions)}"
        )


def validate_file_name(value):
    """
    Check file extension against the general upload allowlist, reject native
    executable content, and sanitize the file name.
    """
    reject_executable_content(value)
    return _validate_file_extension_and_sanitize(value, ALLOWED_UPLOAD_EXTENSIONS)


def validate_html_template_file_name(value):
    """
    Filename check for HTML layout templates (server-side WeasyPrint templates,
    rendered by the platform and never served as attachments). `.html` is allowed
    here even though it is excluded from the general upload allowlist.
    """
    return _validate_file_extension_and_sanitize(value, ["html"])

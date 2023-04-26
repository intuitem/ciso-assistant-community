from django.db import connection
from iam.models import Folder


def ROOT_FOLDER(): return None if not connection.introspection.table_names() else (
    Folder.objects.get(content_type=Folder.ContentType.ROOT) if Folder.objects.filter(
        content_type=Folder.ContentType.ROOT).exists() else None
)

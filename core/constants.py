from django.shortcuts import get_object_or_404
from iam.models import Folder

ROOT_FOLDER = get_object_or_404(Folder, content_type=Folder.ContentType.ROOT)
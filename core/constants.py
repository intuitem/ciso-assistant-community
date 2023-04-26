from iam.models import Folder

ROOT_FOLDER = Folder.objects.get(content_type=Folder.ContentType.ROOT)
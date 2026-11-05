from django.db import models
from django.utils.html import format_html

from iam.models import Folder


class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    IAM_SCOPE_FIELD = Folder.IAM_NOT_IMPLEMENTED

    @property
    def get_html_url(self):
        url = ""
        return format_html('<a class="bg-blue-100" href="{}"> {} </a>', url, self.name)

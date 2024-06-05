from django.db import models
from django.utils.html import format_html


class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    @property
    def get_html_url(self):
        url = ""
        return format_html('<a class="bg-blue-100" href="{}"> {} </a>', url, self.name)

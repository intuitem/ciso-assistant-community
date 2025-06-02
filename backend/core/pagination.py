from rest_framework.pagination import LimitOffsetPagination
from urllib.parse import urlparse


class CustomLimitOffsetPagination(LimitOffsetPagination):
    def get_next_link(self):
        next_link = super().get_next_link()
        if next_link is None:
            return None
        # Extract just the path and query components
        parsed = urlparse(next_link)
        return f"{parsed.path}?{parsed.query}"

    def get_previous_link(self):
        previous_link = super().get_previous_link()
        if previous_link is None:
            return None
        # Extract just the path and query components
        parsed = urlparse(previous_link)
        return f"{parsed.path}?{parsed.query}"

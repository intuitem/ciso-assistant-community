import structlog
from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)


def _bounded_int(value, minimum):
    number = int(value)
    if number < minimum:
        raise ValueError()
    return number


class CustomLimitOffsetPagination(LimitOffsetPagination):
    # PAGINATE_BY is the default page size, PAGINATE_MAX the hard ceiling:
    # larger ?limit= values are clamped to max_limit.
    max_limit = settings.PAGINATE_MAX

    # Stock DRF silently falls back to the defaults on invalid limit/offset
    # values (limit=0 historically read as "no limit" but never was). Reject
    # them instead so broken clients fail loudly rather than get a silently
    # truncated dataset.
    def get_limit(self, request):
        param = request.query_params.get(self.limit_query_param)
        if param is None:
            return self.default_limit
        try:
            requested = _bounded_int(param, minimum=1)
        except ValueError:
            raise ValidationError(
                {self.limit_query_param: "expected a strictly positive integer"}
            )
        if requested > self.max_limit:
            # Clients asking above the ceiling are exactly the ones a lower
            # ceiling would truncate: record them while it is still generous.
            logger.warning(
                "pagination limit clamped",
                requested=requested,
                served=self.max_limit,
                path=request.path,
            )
            return self.max_limit
        if requested > settings.PAGINATE_TARGET_MAX:
            # Served today, truncated if the ceiling ever drops to the target.
            logger.info(
                "pagination limit above target ceiling",
                requested=requested,
                target=settings.PAGINATE_TARGET_MAX,
                path=request.path,
            )
        return requested

    def get_offset(self, request):
        param = request.query_params.get(self.offset_query_param)
        if param is None:
            return 0
        try:
            return _bounded_int(param, minimum=0)
        except ValueError:
            raise ValidationError(
                {self.offset_query_param: "expected a non-negative integer"}
            )

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

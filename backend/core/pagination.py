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
    max_limit = settings.PAGINATE_MAX

    # Stock DRF falls back to the default on an invalid limit/offset; reject
    # instead, so a broken client fails loudly rather than silently truncating.
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
            logger.warning(
                "pagination limit clamped",
                requested=requested,
                served=self.max_limit,
                path=request.path,
            )
            return self.max_limit
        if requested > settings.PAGINATE_TARGET_MAX:
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

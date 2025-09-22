from rest_framework.routers import DefaultRouter


class RouterFactory:
    def __init__(
        self,
    ) -> None:
        pass

    def create_router(self, enforce_trailing_slash: bool) -> DefaultRouter:
        if enforce_trailing_slash:
            return DefaultRouter()
        return OptionalSlashRouter()


class OptionalSlashRouter(DefaultRouter):
    """
    DefaultRouter which makes the trailing slash optional.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = "/?"

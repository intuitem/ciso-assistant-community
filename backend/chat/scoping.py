"""
Read scoping for chat.

Chat used to scope reads by accessible *folders* — a ``view_folder`` check.
The REST API scopes by ``RoleAssignment``-resolved object ids, i.e. a per-model
``view_<model>`` check within those folders. The two are not the same, and
models scoped through a relation (Solution via provider_entity) have no folder
of their own at all. Everything chat reads goes through this object-level check
so it can never return more than the API would.
"""

RESPONDENT_SCOPED_MODELS = {
    "core.ComplianceAssessment",
    "core.RequirementAssessment",
    "core.RequirementAssignment",
}


class ReadScope:
    """Objects a user may read, resolved per model and cached for the request."""

    def __init__(self, user):
        self.user = user
        self._object_ids: dict[str, list] = {}
        self._object_id_sets: dict[str, set[str]] = {}
        self._model_folder_ids: dict[str, list[str]] = {}
        self._folder_ids: list[str] | None = None
        self._respondent_folder_ids: set | None = None

    def _respondent_folders(self, model_class) -> set:
        if model_class._meta.label not in RESPONDENT_SCOPED_MODELS:
            return set()
        if self._respondent_folder_ids is None:
            from core.utils import get_respondent_scoped_folder_ids

            self._respondent_folder_ids = get_respondent_scoped_folder_ids(self.user)
        return self._respondent_folder_ids

    @property
    def folder_ids(self) -> list[str]:
        """Accessible domain folders — for name resolution and folder choices."""
        if self._folder_ids is None:
            from .rag import get_accessible_folder_ids

            self._folder_ids = get_accessible_folder_ids(self.user)
        return self._folder_ids

    def readable_ids(self, model_class) -> list:
        key = model_class._meta.label
        if key not in self._object_ids:
            from iam.models import Folder, RoleAssignment

            ids = RoleAssignment.get_viewable_object_ids(self.user, model_class)
            if respondent_folders := self._respondent_folders(model_class):
                ids = (
                    model_class.objects.filter(id__in=ids)
                    .exclude(folder_id__in=respondent_folders)
                    .values_list("id", flat=True)
                )
            self._object_ids[key] = list(ids)
        return self._object_ids[key]

    def can_read(self, model_class, object_id) -> bool:
        key = model_class._meta.label
        if key not in self._object_id_sets:
            self._object_id_sets[key] = {str(i) for i in self.readable_ids(model_class)}
        return str(object_id) in self._object_id_sets[key]

    def queryset(self, model_class):
        return model_class.objects.filter(id__in=self.readable_ids(model_class))

    def folder_ids_for(self, model_class) -> list[str]:
        """
        Folders where the user holds ``view_<model>``.

        For payload-level filtering (Qdrant) where an id list would be huge and
        only the folder is stored. Every indexed model is folder-scoped, and the
        indexer writes that same folder into the payload, so this is exact.
        """
        key = model_class._meta.label
        if key not in self._model_folder_ids:
            from iam.models import Folder, RoleAssignment

            respondent_folders = self._respondent_folders(model_class)
            self._model_folder_ids[key] = [
                str(fid)
                for fid in RoleAssignment.get_allowed_folder_ids(
                    self.user, ("view", model_class)
                )
                if fid not in respondent_folders
            ]
        return self._model_folder_ids[key]

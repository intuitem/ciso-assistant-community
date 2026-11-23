import ast
import inspect
import textwrap

from django.apps import apps

from automation.workflows.models import WorkflowInstance
from core.models import Assessment, Commitment, RequirementNodeAttachment

# No `folder_from` here, the serializer's post-save check covers them: Assessment,
# WorkflowInstance and RequirementNodeAttachment only fill the folder from the
# parent when it is unset (or root); Commitment's parent is a GenericForeignKey.
FOLDER_FROM_EXEMPT = {
    Assessment,
    Commitment,
    WorkflowInstance,
    RequirementNodeAttachment,
}


def _folder_source(model):
    """The first FK in a `self.folder = self.<fk>[...].folder` in any save() of
    the model's MRO, the class owning that save(), or (None, None)."""
    for klass in model.__mro__:
        if "save" not in klass.__dict__ or klass.__module__.startswith("django"):
            continue
        try:
            tree = ast.parse(textwrap.dedent(inspect.getsource(klass.save)))
        except OSError, SyntaxError:  # pragma: no cover - source always ships
            continue
        for statement in ast.walk(tree):
            if not isinstance(statement, ast.Assign):
                continue
            target, value = statement.targets[0], statement.value
            if not (
                isinstance(target, ast.Attribute)
                and target.attr in ("folder", "folder_id")
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and isinstance(value, ast.Attribute)
                and value.attr in ("folder", "folder_id")
            ):
                continue
            chain = value.value
            while isinstance(chain, ast.Attribute) and isinstance(
                chain.value, ast.Attribute
            ):
                chain = chain.value
            if (
                isinstance(chain, ast.Attribute)
                and isinstance(chain.value, ast.Name)
                and chain.value.id == "self"
            ):
                return chain.attr, klass
    return None, None


def test_models_declare_folder_from_when_save_derives_the_folder():
    for model in apps.get_models():
        declared = getattr(model, "folder_from", None)
        derived, owner = _folder_source(model)
        label = model._meta.label
        if owner in FOLDER_FROM_EXEMPT:
            assert declared is None, label
            continue
        assert declared == derived, label
        if declared:
            assert model._meta.get_field(declared).many_to_one, label

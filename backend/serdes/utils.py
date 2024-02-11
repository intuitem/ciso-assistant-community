from typing import Iterable

import django.apps
from django.core import serializers
from django.db.models import Model
from django.db.models.deletion import Collector

from iam.models import Folder


def get_all_objects():
    """
    Get all objects in the database.

    Returns:
    --------
    objects: list
        List of objects in the database.
    """
    objects = list()
    for app in django.apps.apps.get_app_configs():
        for model in app.get_models():
            objects.extend(model.objects.all())
    return objects


def dump_objects(queryset: Iterable[Model], path: str, format: str = "json"):
    """
    Dump objects to a file.

    Parameters:
    -----------
    queryset: Iterable[Model]
        Queryset of objects to dump.
    path: str
        Path to the file to dump to.
    format: str
        Format to dump to. Default is 'json'.
    """
    serialized_objects = serializers.serialize(format, queryset)
    if path == "-":
        print(serialized_objects)
    else:
        with open(path, "w") as outfile:
            outfile.write(serialized_objects)
    return path


def get_objects_from_folder(folder: Folder) -> set:
    """
    Collates all objects in a folder.

    Parameters:
    -----------
    folder: Folder
        Folder to get objects from.

    Returns:
    --------
    objects: list
        List of objects in the folder.
    """
    objects = set()
    # NOTE: This is a hack to get all objects in a folder.
    #       As all objects contained in a folder are deleted
    #       when the folder is deleted, we can use the Django
    #       deletion collector to get all the objects in a folder.
    collector = Collector(using="default")
    collector.collect([folder])

    for model, model_instances in collector.data.items():
        objects.update(model_instances)

    return objects


def restore_objects(path: str, format: str = "json"):
    """
    Restore objects from a file.

    Parameters:
    -----------
    path: str
        Path to the file to restore from.
    format: str
        Format to restore from. Default is 'json'.
    """
    with open(path, "r") as infile:
        serialized_objects = infile.read()
    objects = serializers.deserialize(format, serialized_objects)
    for obj in objects:
        obj.save()
    return path

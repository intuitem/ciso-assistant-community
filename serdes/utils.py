from django.core import serializers
import django.apps


def get_all_objects():
    '''
    Get all objects in the database.

    Returns:
    --------
    objects: list
        List of objects in the database.
    '''
    objects = list()
    for app in django.apps.apps.get_app_configs():
        for model in app.get_models():
            objects.extend(model.objects.all())
    return objects


def serialize_objects(objects, format='json'):
    '''
    Serialize objects to chosen format.

    Parameters:
    -----------
    objects: list
        List of objects to serialize.
    format: str
        Format to serialize to. e.g. json, jsonl, yaml, xml.

    Returns:
    --------
    serialized_objects: str
        Serialized objects.
    '''
    return serializers.serialize(format, objects)


def deserialize_objects(path, format='json'):
    '''
    Deserialize objects from a file.

    Parameters:
    -----------
    path: str
        Path to file to deserialize from.
    format: str
        Format to deserialize from. e.g. json, yaml, xml.

    Returns:
    --------
    path: str
        Path to file to deserialize from.
    '''
    objects = list()
    with open(path, 'r') as infile:
        for object in serializers.deserialize(format, infile):
            objects.append(object)
    return objects


def create_backup(path, format='json'):
    '''
    Create a backup of the current state of the database.

    Parameters:
    -----------
    path: str
        Path to file to backup to.
    format: str
        Format to backup to. e.g. json, jsonl, yaml, xml.
    '''
    objects = get_all_objects()
    serialized_objects = serialize_objects(objects, format)
    with open(path, 'w') as outfile:
        outfile.write(serialized_objects)
    return path

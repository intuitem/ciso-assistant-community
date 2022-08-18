from django.core import serializers

def serialize_objects(objects, path, format="json"):
    '''
    Serialize objects to a file.

    Parameters:
    -----------
    objects: list
        List of objects to serialize.
    path: str
        Path to file to serialize to.
    format: str
        Format to serialize to. This includes json, jsonl, yaml, xml.

    Returns:
    --------
    path: str
        Path to file to serialize to.
    '''
    with open(path, 'w') as outfile:
        outfile.write(serializers.serialize(format, objects))
    return path

def deserialize_objects(path, format="json"):
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
    with open(path, 'r') as infile:
        for object in serializers.deserialize(format, infile):
            object.save()
    return path

from core.models import Threat, SecurityFunction, Framework, Requirement, RequirementGroup, RequirementLevel
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.db import models
from iam.models import Folder, RoleAssignment
from ciso_assistant import settings
from django.utils.translation import gettext_lazy as _

from .validators import *

import os
import yaml


def get_available_library_files():
    '''
    Returns a list of available library files
    
    Returns:
        files: list of available library files
    '''
    files = []
    path = settings.BASE_DIR / 'library/libraries'
    for f in os.listdir(path):
        if os.path.isfile(os.path.join(path, f)) and f.endswith('.yaml') or f.endswith('.yml'):
            files.append(f)
    return files


def get_available_libraries():
    '''
    Returns a list of available libraries
    
    Returns:
        libraries: list of available libraries
    '''
    files = get_available_library_files()
    path = settings.BASE_DIR / 'library/libraries'
    libraries = []
    for f in files:
        with open(path / f, 'r', encoding='utf-8') as file:
            libs = yaml.safe_load_all(file)
            for l in list(libs):
                libraries.append(l)
    return libraries


def get_library_names(libraries):
    '''
    Returns a list of available library names
    
    Returns:
        names: list of available library names
    '''
    names = []
    for l in libraries:
        names.append(l['name'])
    return names


def get_library(urn):
    '''
    Returns a library by urn
    
    Args:
        urn: urn of the library to return
        
    Returns:
        library: library with the given urn
    '''
    libraries = get_available_libraries()
    for l in libraries:
        if l['urn'] == urn:
            return l
    return None


def get_library_items(library, type: str) -> list[dict]:
    '''
    Returns a list of items of a given type from a library
    
    Args:
        library: library to return items from
        type: type of items to return
        
    Returns:
        items: list of items of the given type from the library
    '''
    return library['objects'].get(type, [])


def import_requirement_group(framework_urn: str, fields: dict):
    '''
    Imports a requirement group from a framework
    
    Args:
        fields: requirement group fields
        
    Returns:
        requirement_group: imported requirement group
    '''
    required_fields = ['name']

    if not validate_object(required_fields, fields):
        raise Exception('Invalid requirement group')
    
    _framework: Framework = Framework.objects.get(urn=framework_urn)
    _parent_urn = fields.get('parent_urn', None)
    _urn=fields.get('urn', None)

    requirement_group = RequirementGroup.objects.update_or_create(
        defaults = {
            "framework": _framework,
            "urn": _urn,
            "parent_urn": _parent_urn,
            "order_id": _framework.get_next_order_id(RequirementGroup, _parent_urn),
            "name": fields['name'],
            "description": fields['description'] if "description" in fields else "",
            "level": fields.get('level', None),
            "folder": _framework.folder
        },
        urn=_urn,
    )


def import_requirement_level(framework_urn: str, fields: dict):
    '''
    Imports a requirement level from a framework
    
    Args:
        fields: requirement level fields
        
    Returns:
        requirement_level: imported requirement level
    '''
    required_fields = ['level']

    if not validate_object(required_fields, fields):
        raise Exception('Invalid requirement level')
    
    _framework: Framework = Framework.objects.get(urn=framework_urn)
    _urn=fields.get('urn', None)

    requirement_level = RequirementLevel.objects.update_or_create(
        defaults = {
            "framework": _framework,
            "urn": _urn,
            "description": fields['description'] if "description" in fields else "",
            "level": fields['level'],
            "folder": _framework.folder
        },
        urn=_urn,
    )


def import_requirement(framework_urn: str, fields: dict):
    """
    Imports a requirement from a framework

    Args:
        framework_urn: urn of the framework to import the requirement from
        parentr_urn: urn of the parent object
        fields: requirement fields

    Returns:
        requirement: imported requirement
    """
    required_fields = ['name']

    if not validate_object(required_fields, fields):
        raise Exception('Invalid requirement')
    
    _framework: Framework = Framework.objects.get(urn=framework_urn)
    _parent_urn = fields.get('parent_urn', None)
    _urn=fields.get('urn', None)

    requirement = Requirement.objects.update_or_create(
        defaults = {
            "framework": _framework,
            "urn": _urn,
            "parent_urn": _parent_urn,
            "order_id": _framework.get_next_order_id(Requirement, _parent_urn),
            "name": fields['name'],
            "description": fields['description'] if "description" in fields else "",
            "level": fields.get('level', None), 
            "folder":_framework.folder
        },
        urn=_urn
    )

    for threat in fields.get('threats', []):
        requirement[0].threats.add(Threat.objects.get(urn=threat))

    for security_function in fields.get('security_functions', []):
        requirement[0].security_functions.add(SecurityFunction.objects.get(urn=security_function))


def import_framework(fields: dict):
    '''
    Imports a framework from a library
    
    Args:
        fields: framework fields
        
    Returns:
        framework: imported framework
    '''
    required_fields = ['name']

    if not validate_object(required_fields, fields):
        raise Exception('Invalid framework')
    
    print(f"Importing framework: {fields['name']}")

    _urn=fields.get('urn', None)

    framework = Framework.objects.update_or_create(
        defaults = {
            "urn": _urn,
            "name": fields['name'],
            "description": fields['description'],
            "version": fields.get('version', None),
            "folder": Folder.get_root_folder() # TODO: make this configurable
        },
        urn=_urn
    )


def import_threat(fields: dict):
    '''
    Imports a threat from a library
    
    Args:
        fields: threat fields
        
    Returns:
        threat: imported threat
    '''
    required_fields = ['name']

    if not validate_object(required_fields, fields):
        raise Exception('Invalid threat')

    _urn=fields.get('urn', None)

    threat = Threat.objects.update_or_create(
        defaults = {
            "urn": _urn,
            "name": fields['name'],
            "description": fields['description'],
            "version": fields.get('version', None),
            "folder": Folder.get_root_folder() # TODO: make this configurable
        },
        urn=_urn
    )


def import_security_function(fields: dict):
    '''
    Imports a security function from a library
    
    Args:
        fields: security function fields
        
    Returns:
        security_function: imported security function
    '''
    required_fields = ['name']

    if not validate_object(required_fields, fields):
        raise Exception('Invalid security function')

    _urn=fields.get('urn', None)
    security_function = SecurityFunction.objects.update_or_create(
        defaults = {
            "urn": _urn,
            "name": fields['name'],
            "description": fields['description'],
            "version": fields.get('version', None),
            "provider": fields.get('provider', None),
            "typical_evidence": fields.get('typical_evidence', None),
            "folder": Folder.get_root_folder() # TODO: make this configurable
        },
        urn=_urn
    )


def import_objects(objects: dict):
    '''
    Imports a library
    
    Args:
        library: library to import
    '''
    threats = objects.get('threats', [])
    security_functions = objects.get('security_functions', [])
    framework = objects.get('framework', {})

    for threat in threats:
        import_threat(threat)

    for security_function in security_functions:
        import_security_function(security_function)

    if framework:
        import_framework(framework)

    for requirement_level in framework.get('requirement_levels', []):
        import_requirement_level(framework_urn=framework['urn'], fields=requirement_level)
    for requirement_group in framework.get('requirement_groups', []):
        import_requirement_group(framework_urn=framework['urn'], fields=requirement_group)
    for requirement in framework.get('requirements', []):
        import_requirement(framework_urn=framework['urn'], fields=requirement)


def is_import_allowed(request, object_type):
    '''
    Verify user permissions to import a library

    Args:
        object_type: type of the object being imported
    '''
    object_type = object_type.replace("_", "")
    if not RoleAssignment.is_access_allowed(request.user, Permission.objects.get(codename=f"add_{object_type}"), Folder.get_root_folder()):
        messages.error(request, _("Library was not imported: permission denied for: {}").format(object_type))
        raise Exception(_("Permission denied for: {}").format(object_type))
    return True


def import_library_view(request, library):
    '''
    Imports a library
    
    Args:
        request: request object
        library: library to import
    '''
    # TODO: refactor this

    objects_imported = {}
    objects = library.get('objects', {})
    framework = objects.get('framework', {})
    requirement_levels = framework.get('requirement_levels', [])
    requirement_groups = framework.get('requirement_groups', [])
    requirements = framework.get('requirements', [])
    threats = objects.get('threats', [])
    security_functions = objects.get('security_functions', [])

    objects_imported['threats'] = threats
    objects_imported['security_functions'] = security_functions
    objects_imported['framework'] = framework
    objects_imported['requirement_levels'] = requirement_levels
    objects_imported['requirement_groups'] = requirement_groups
    objects_imported['requirements'] = requirements
    import_objects(objects_imported)
    messages.success(request, _('Library "{}" imported successfully.').format(library["name"]))
    return True
from tkinter import E
from core.models import RiskMatrix
from back_office.models import Threat, SecurityFunction
from django.contrib import messages
from iam.models import Folder

from .validators import *

import os
import json

def get_available_package_files():
    '''
    Returns a list of available package files
    
    Returns:
        files: list of available package files
    '''
    files = []
    path = r'./library/packages'
    # print absolute path
    print(os.path.abspath(path))
    for f in os.listdir(path):
        if os.path.isfile(os.path.join(path, f)) and f.endswith('.json'):
            files.append(f)
    return files

def get_available_packages():
    '''
    Returns a list of available packages
    
    Returns:
        packages: list of available packages
    '''
    files = get_available_package_files()
    path = r'./library/packages'
    packages = []
    for f in files:
        with open(f'{path}/{f}', 'r', encoding='utf-8') as file:
            packages.append(json.load(file))
    return packages

def get_package_names():
    '''
    Returns a list of available package names
    
    Returns:
        names: list of available package names
    '''
    packages = get_available_packages()
    names = []
    for p in packages:
        names.append(p['name'])
    return names

def get_package(name):
    '''
    Returns a package by name
    
    Args:
        name: name of the package to return
        
    Returns:
        package: package with the given name
    '''
    packages = get_available_packages()
    for p in packages:
        if p['name'] == name: # TODO: use slug or cook-up some unique id instead of using 'name'
            return p
    return None

def import_matrix(request, fields):
    '''
    Imports a matrix from a package
    
    Args:
        fields: matrix fields
        
    Returns:
        matrix: imported matrix
    '''
    required_fields = ['name', 'description', 'probability', 'impact', 'risk', 'grid']

    if not object_valid(required_fields, fields):
        messages.error(request, 'Package was not imported: Invalid matrix.')
        raise Exception('Invalid matrix')
    
    matrix = RiskMatrix.objects.create(
        name=fields['name'],
        description=fields['description'],
        json_definition=json.dumps(fields),
        folder=Folder.objects.get(content_type=Folder.ContentType.ROOT) # TODO: make this configurable
    )

    return matrix

def import_threat(request, fields):
    '''
    Imports a threat from a package
    
    Args:
        fields: threat fields
        
    Returns:
        threat: imported threat
    '''
    required_fields = ['name', 'description']

    if not object_valid(required_fields, fields):
        messages.error(request, 'Package was not imported: Invalid threat.')
        raise Exception('Invalid threat')

    threat = Threat.objects.create(
        name=fields['name'],
        description=fields['description'],
        folder=Folder.objects.get(content_type=Folder.ContentType.ROOT) # TODO: make this configurable
    )

    return threat

def import_security_function(request, fields):
    '''
    Imports a security function from a package
    
    Args:
        fields: security function fields
        
    Returns:
        security_function: imported security function
    '''
    required_fields = ['name', 'description']

    if not object_valid(required_fields, fields):
        messages.error(request, 'Package was not imported: Invalid security function.')
        raise Exception('Invalid security function')

    security_function = SecurityFunction.objects.create(
        name=fields['name'],
        description=fields['description'],
        provider=fields['provider'],
        contact=fields['contact'],
        folder=Folder.objects.get(content_type=Folder.ContentType.ROOT) # TODO: make this configurable
    )

    return security_function

def ignore_package_object(package_objects, object_type):
    '''
    Return two lists of objects to ignore or upload

    Args:
        package_objects: objects to filter
        object_type: type of the objects
    '''
    ignored_list = []
    uploaded_list = []
    for package_object in package_objects:
        if object_type.objects.filter(name=package_object['name']).exists():
            ignored_list.append(package_object)
        else:
            uploaded_list.append(package_object)
    return uploaded_list, ignored_list

def import_package(request, package):
    '''
    Imports a package
    
    Args:
        package: package to import
    '''
    matrices = []
    threats = []
    security_functions = []
    objects_uploaded = 0
    objects_ignored = 0

    for obj in package.get('objects'):
        if obj['type'] == 'matrix':
            matrices.append(obj.get('fields'))
        elif obj['type'] == 'threat':
            threats.append(obj.get('fields'))
        elif obj['type'] == 'security_function':
            security_functions.append(obj.get('fields'))
        else:
            messages.error(request, f'Package was not imported: Unknown object type: {obj["type"]}')
            raise Exception(f'Unknown object type: {obj["type"]}')

    uploaded_list, ignored_list = ignore_package_object(matrices, RiskMatrix)
    objects_ignored += len(ignored_list)
    objects_uploaded += len(uploaded_list)
    for matrix in matrices:
        import_matrix(request, matrix)

    uploaded_list, ignored_list = ignore_package_object(threats, Threat)
    objects_ignored += len(ignored_list)
    objects_uploaded += len(uploaded_list)
    for threat in uploaded_list:
        import_threat(request, threat)

    uploaded_list, ignored_list = ignore_package_object(security_functions, SecurityFunction)
    objects_ignored += len(ignored_list)
    objects_uploaded += len(uploaded_list)
    for security_function in uploaded_list:
        import_security_function(request, security_function)

    messages.success(request, f'Package "{package["name"]}" imported successfully. {objects_uploaded} objects imported and {objects_ignored} objects ignored.')
    return True
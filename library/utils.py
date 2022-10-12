from genericpath import isfile
import os
import json

def get_available_package_files():
    files = []
    path = r'./library/packages'
    # print absolute path
    print(os.path.abspath(path))
    for f in os.listdir(path):
        if os.path.isfile(os.path.join(path, f)) and f.endswith('.json'):
            files.append(f)
    return files

def get_available_packages():
    files = get_available_package_files()
    path = r'./library/packages'
    packages = []
    for f in files:
        with open(f'{path}/{f}', 'r', encoding='utf-8') as file:
            packages.append(json.load(file))
    return packages

def get_package_names():
    packages = get_available_packages()
    names = []
    for p in packages:
        names.append(p['name'])
    return names

def get_package(name):
    packages = get_available_packages()
    for p in packages:
        if p['name'] == name: # TODO: use slug or cook-up some unique id instead of using 'name'
            return p
    return None

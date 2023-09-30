from core.models import *

def preview_library(library) -> list:
    """
    Function to create temporary requirements and requirement groups lists
    Used to display requirements in tree view inside library detail view
    """
    preview = {}
    requirement_groups_list = []
    requirements_list = []
    if library['objects']['framework'].get('requirement_groups'):
        for requirement_group in library['objects']['framework']['requirement_groups']:
            requirement_groups_list.append(
                RequirementGroup(description = requirement_group.get('description'),
                                name = requirement_group['name'],
                                urn = requirement_group['urn'],
                                parent_urn = requirement_group.get('parent_urn')))
    for requirement in library['objects']['framework']['requirements']:
        if Requirement.objects.filter(urn=requirement['urn']).exists():
            requirements_list.append(Requirement.objects.get(urn=requirement['urn']))
        else:
            temp_req = Requirement(description = requirement.get('description'),
                                                    name = requirement['name'],
                                                    urn = requirement['urn'],
                                                    parent_urn = requirement.get('parent_urn'),
                                                    folder = Folder.get_root_folder())
            requirements_list.append(temp_req)
    preview['requirement_groups'] = requirement_groups_list
    preview['requirements'] = requirements_list
    return preview

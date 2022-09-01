from back_office.models import *
from general.models import *
from django.contrib.auth.models import Permission

auditor_permissions = Permission.objects.filter(codename__in=["view_analysis", 
"view_mitigation", 
"view_riskacceptance",
"view_riskinstance",
"view_asset",
"view_parentrisk",
"view_project",
"view_solution"])

analyst_permissions = Permission.objects.filter(codename__in=["change_analysis",
"view_analysis",
"change_mitigation",
"view_mitigation",
"change_riskacceptance",
"view_riskacceptance",
"change_riskinstance",
"view_riskinstance",
"change_asset",
"view_asset",
"change_parentrisk",
"view_parentrisk",
"change_project",
"view_project",
"change_solution",
"view_solution"])

domain_manager_permissions = Permission.objects.filter(codename__in=["change_usergroup",
"view_usergroup",
"add_analysis",
"change_analysis",
"delete_analysis",
"view_analysis",
"add_mitigation",
"change_mitigation",
"delete_mitigation",
"view_mitigation",
"add_riskacceptance",
"change_riskacceptance",
"delete_riskacceptance",
"view_riskacceptance",
"add_riskinstance",
"change_riskinstance",
"delete_riskinstance",
"view_riskinstance",
"add_asset",
"change_asset",
"delete_asset",
"view_asset",
"add_folder",
"change_folder",
"delete_folder",
"view_folder",
"add_parentrisk",
"change_parentrisk",
"delete_parentrisk",
"view_parentrisk",
"add_project",
"change_project",
"delete_project",
"view_project",
"add_solution",
"change_solution",
"delete_solution",
"view_solution"])

administrator_permissions = Permission.objects.filter(codename__in=["add_user",
"change_user",
"delete_user",
"view_user",
"add_roleassignment",
"change_roleassignment",
"delete_roleassignment",
"view_roleassignment",
"add_usergroup",
"change_usergroup",
"delete_usergroup",
"view_usergroup",
"add_event",
"change_event",
"delete_event",
"view_event",
"add_asset",
"change_asset",
"delete_asset",
"view_asset",
"add_folder",
"delete_folder",
"view_folder",
"add_parentrisk",
"change_parentrisk",
"delete_parentrisk",
"view_parentrisk",
"add_solution",
"change_solution",
"delete_solution",
"view_solution"])

root = Folder.objects.create(name="Global", content_type="GL")

auditor = Role.objects.create(name="Auditor")
auditor.permissions.set(auditor_permissions)
analyst= Role.objects.create(name="Analyst")
analyst.permissions.set(analyst_permissions)
domain_manager = Role.objects.create(name="Domain Manager")
domain_manager.permissions.set(domain_manager_permissions)
administrator = Role.objects.create(name="Administrator")
administrator.permissions.set(administrator_permissions)

administrators = UserGroup.objects.create(name="Administrators", folder = root)
global_auditors = UserGroup.objects.create(name="Global auditors", folder = root)
ra1 = RoleAssignment.objects.create(isUserGroup=True, userGroup=administrators, role=administrator)
ra1.folders.add(root)
ra2 = RoleAssignment.objects.create(isUserGroup=True, userGroup=global_auditors, role=auditor)
ra2.folders.add(root)
from django.contrib import admin 
from .models import User, Role, Permission, RoleAssignment, UserGroup 

@admin.register(User) 
class CustomUserAdmin(admin.ModelAdmin): 
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser'] 
    search_fields = ['email', 'first_name', 'last_name'] 

admin.site.register(Role) 
admin.site.register(Permission) 
admin.site.register(RoleAssignment) 
admin.site.register(UserGroup) 
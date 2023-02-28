from django.contrib import admin

from controller.models import Client

class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin_email')

admin.site.register(Client, ClientAdmin)


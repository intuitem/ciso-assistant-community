from django.http import HttpResponse
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core import management
from django.core.management.commands import loaddata, dumpdata

from iam.models import RoleAssignment

import sys

from .forms import *


class BackupRestoreView(FormView):
    template_name = 'serdes/backup_restore.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('backup-restore')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['change_usergroup'] = RoleAssignment.has_permission(self.request.user, "change_usergroup")
        context['view_user'] = RoleAssignment.has_permission(self.request.user, "view_user")
        return context
    
    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        file = request.FILES.get('file')
        
        if form.is_valid():
            if file:
                sys.stdin = file.file
                management.call_command('flush', interactive=False)
                management.call_command(loaddata.Command(), '-', format="json", verbosity=0, exclude=['contenttypes', 'auth.permission'])
                print(request, 'Database restored successfully.')
            else:
                print(request, 'No file selected.')
            return self.form_valid(form)
        else:
            print(request, f'Invalid form.')
            return self.form_invalid(form)


def dump_db_view(request):
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="db.json"'
    management.call_command(dumpdata.Command(), exclude=['contenttypes', 'auth.permission'], indent=4, stdout=response, natural_foreign=True)
    return response
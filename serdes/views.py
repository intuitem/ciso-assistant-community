from django.http import HttpResponse
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core import management
from django.core.management.commands import loaddata, dumpdata
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test

from iam.models import RoleAssignment
from back_office.utils import UserGroupCodename
from asf_rm.settings import VERSION

import re
import sys
import io

from .forms import *

def is_superuser_check(user):
    return user.is_superuser


class BackupRestoreView(FormView, UserPassesTestMixin):
    template_name = 'serdes/backup_restore.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('backup-restore')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['change_usergroup'] = RoleAssignment.has_permission(self.request.user, "change_usergroup")
        context['view_user'] = RoleAssignment.has_permission(self.request.user, "view_user")
        return context

    def dispatch(self, request, *args, **kwargs):
        if not is_superuser_check(request.user):
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        file = request.FILES.get('file')
        
        if form.is_valid():
            if file:
                # NOTE: This method implies we trust the data in the file.
                # Here we are scrubbing the metadata from the file, as loaddata expects a raw dump.
                head_pattern = r'.+?(?=,\n*\[\n*{\n\s*"model").\n'
                tail_pattern = r']\Z'
                file_content = file.read().decode('utf-8')
                trimmed_content = re.sub(head_pattern, '', file_content)
                trimmed_content = re.sub(tail_pattern, '', trimmed_content)
                
                # NOTE: This method is not safe, as we do not check the file extension and content.
                #       Furthermore, this is not suitable to load data from selected folders
                sys.stdin = io.StringIO(trimmed_content)
                management.call_command('flush', interactive=False)

                # Here we load the data from stdin
                management.call_command(loaddata.Command(), '-', format="json", verbosity=0, exclude=['contenttypes', 'auth.permission'])
                print(request, 'Database restored successfully.')
            else:
                print(request, 'No file selected.')
            return self.form_valid(form)
        else:
            print(request, f'Invalid form.')
            return self.form_invalid(form)

    def test_func(self):
        return is_superuser_check(self.request.user)


@user_passes_test(is_superuser_check)
def dump_db_view(request):
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="db.json"'

    response.write(f'[{{"meta": [{{"media_version": "{VERSION}"}}]}},\n')
    # Here we dump th data to stdout
    # NOTE: We will not be able to dump selected folders with this method.
    management.call_command(dumpdata.Command(), exclude=['contenttypes', 'auth.permission'], indent=4, stdout=response, natural_foreign=True)
    response.write(']')
    return response
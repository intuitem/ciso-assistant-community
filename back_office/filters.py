from attr import attrs
from django.forms import CharField, CheckboxInput, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, widgets
from django_filters import *

from core.models import Analysis
from general.models import Project
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class StyledFilterSet(FilterSet):
    pass
    # def __init__(self, *args, **kwargs):
    #     super(__class__, self).__init__(*args, **kwargs)
    #     text_inputs = (TextInput, NumberInput, EmailInput, URLInput, PasswordInput, HiddenInput, DateInput, DateTimeInput, TimeInput)
    #     select_inputs = (Select, SelectMultiple, NullBooleanSelect)
    #     print('\n\nFILTERS:\n')
    #     print(self.filters.items())
    #     for fname, f in self.filters.fields.items():
    #         input_type = f.widget.__class__
    #         model_name = str(self.Meta.model).split('.')[-1].strip("'>").lower()
    #         if input_type in text_inputs:
    #             f.widget.attrs['id'] = f'id_{model_name}_{fname}'
    #             f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
    #         if input_type in select_inputs:
    #             f.widget.attrs['id'] = f'id_{model_name}_{fname}'
    #             f.widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'

class AnalysisFilter(FilterSet):

    def get_full_names():
        full_names = ()
        users = User.objects.all()
        for user in users:
            full_names += (user.id, user.get_full_name),
        return full_names

    STATUS_CHOICES = (
        (True, _('Yes')),
        (False, _('No')),
    )

    auditor_list = User.objects.all()

    project__name = CharFilter(
        lookup_expr='icontains',
        widget=TextInput(
            attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search Analysis...')
            }))

    is_draft = ChoiceFilter(choices=STATUS_CHOICES)
    auditor = ModelMultipleChoiceFilter(
        queryset=auditor_list,
        )

    auditor = MultipleChoiceFilter(choices=get_full_names,label=('Auditor'))

    project = ModelMultipleChoiceFilter(queryset=Project.objects.all())

    orderby = OrderingFilter(
        empty_label="Order by",
        fields=(
            ('is_draft', 'is_draft'),
            ('auditor', 'auditor'),
            ('updated_at', 'updated_at'),
        )
    )

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        self.filters['is_draft'].field.widget.attrs.update({'class': 'rounded-lg w-full'})
        self.filters['project'].field.widget.attrs.update({'class': 'rounded-lg w-full'})
        self.filters['auditor'].field.widget.attrs.update({'class': 'rounded-lg w-full'})
        self.filters['orderby'].field.widget.attrs.update({
            'class': ' rounded-r-lg border-none focus:ring-0',
            'onchange': 'this.form.submit();'
            })



    class Meta:
        model = Analysis
        fields = ['is_draft', 'auditor', 'project']
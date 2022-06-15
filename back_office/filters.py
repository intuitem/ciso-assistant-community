from logging import critical
from attr import fields
from django.forms import CharField, CheckboxInput, ChoiceField, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, widgets
from django_filters import *
from django_filters.widgets import *

from core.models import Analysis, RiskInstance, Mitigation, Solution, RiskAcceptance
from general.models import Asset, ProjectsGroup, Project, ParentRisk, Solution
from general.models import ParentRisk, Project
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class GenericFilterSet(FilterSet):
    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        # for f in self.filters.items():
        #     print(f[0], f[1].field.widget)
    pass

class GenericOrderingFilter(OrderingFilter):
    def __init__(self, *args, empty_label=_("Order by"), **kwargs):
        super().__init__(self, *args, empty_label=_("Order by"), widget=Select, **kwargs)
        self.field.widget.attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'onchange': 'this.form.submit();'
        }

class GenericModelMultipleChoiceFilter(ModelMultipleChoiceFilter):
    widget=SelectMultiple(
        attrs={
            'class': 'rounded-lg w-full',
        }
    )
    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)

class GenericMultipleChoiceFilter(MultipleChoiceFilter):
    widget=SelectMultiple(
        attrs={
            'class': 'rounded-lg w-full',
        }
    )
    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)

class GenericCharFilter(CharFilter):
    widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0'
        }
    )
    def __init__(self, field_name=None, lookup_expr='icontains', *, label=None, method=None, 
                distinct=False, exclude=False, widget=widget, search_term=None, **kwargs):
        super().__init__(field_name, lookup_expr='icontains', label=label, method=method, 
                        distinct=distinct, exclude=exclude, widget=widget, **kwargs)
        placeholder = f"Search {search_term if search_term else ''}..."
        self.widget.attrs['placeholder'] = placeholder

class GenericChoiceFilter(ChoiceFilter):
    widget=Select(
        attrs={
                'class': 'rounded-lg w-full'
        }
    )
    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)
        

class AnalysisFilter(GenericFilterSet):
    def get_full_names():
        full_names = ()
        users = User.objects.all()
        for user in users:
            full_names += (user.id, user.get_full_name),
        return full_names

    orderby = GenericOrderingFilter(
        fields=(
            ('is_draft', 'is_draft'),
            ('project', 'project'),
            ('auditor', 'auditor'),
            ('updated_at', 'updated_at'),
        ),
        field_labels={
            'is_draft': _('draft'.capitalize()),
            '-is_draft': _('Draft (descending)'),
            'project': _('project'.capitalize()),
            '-project': _('Project (descending)'),
            'auditor': _('auditor'.capitalize()),
            '-auditor': _('Auditor (descending)'),
            'updated_at': _('updated at'.capitalize()),
            '-updated_at': _('Updated at (descending)')
        }
    )

    STATUS_CHOICES = (
        (True, _('Yes')),
        (False, _('No')),
    )

    project__name = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search analysis...')
        }
    ))
    is_draft = GenericChoiceFilter(choices=STATUS_CHOICES)
    auditor = GenericMultipleChoiceFilter(choices=get_full_names(),label=('Auditor'))

    project = GenericModelMultipleChoiceFilter(queryset=Project.objects.all())

    class Meta:
        model = Analysis
        fields = ['is_draft', 'auditor', 'project']

class RiskScenarioFilter(GenericFilterSet):
    title = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search scenario...')
        }
    ))
    parent_risk = GenericModelMultipleChoiceFilter(queryset=ParentRisk.objects.all())
    analysis__project = GenericModelMultipleChoiceFilter(queryset=Project.objects.all())
    treatment = GenericMultipleChoiceFilter(choices=RiskInstance.TREATMENT_OPTIONS)

    orderby = GenericOrderingFilter(
        fields=(
            ('title', 'title'),
            ('parent_risk', 'parent_risk'),
            ('analysis__project', 'analysis__project'),
            ('treatment', 'treatment'),
        ),
        field_labels={
            'title': _('title'.capitalize()),
            '-title': _('Title (descending)'),
            'parent_risk': _('threat'.capitalize()),
            '-parent_risk': _('Threat (descending)'),
            'analysis__project': _('parent'.capitalize() + ' project'),
            '-analysis__project': _('Parent project (descending)'),
            'treatment': _('treatment'.capitalize()),
            '-treatment': _('Treatment (descending)'),
        }
    )

    class Meta:
        model = RiskInstance
        fields = ['title', 'parent_risk', 'analysis__project', 'treatment']

class MeasureFilter(GenericFilterSet):
    title = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search security measure...')
        }
    ))
    risk_instance__analysis__project = GenericModelMultipleChoiceFilter(queryset=Project.objects.all())
    type=GenericMultipleChoiceFilter(choices=Mitigation.MITIGATION_TYPE)
    status=GenericMultipleChoiceFilter(choices=Mitigation.MITIGATION_STATUS)
    solution=GenericModelMultipleChoiceFilter(queryset=Solution.objects.all())

    orderby = GenericOrderingFilter(
        fields=(
            ('status', 'status'),
            ('title', 'title'),
            ('type', 'type'),
            ('risk_instance__analysis__project', 'risk_instance__analysis__project'),
            ('solution', 'solution'),
        ),
        field_labels={
            'status': _('status'.capitalize()),
            '-status': _('Status (descending)'),
            'title': _('title'.capitalize()),
            '-title': _('Title (descending)'),
            'type': _('type'.capitalize()),
            '-type': _('Type (descending)'),
            'risk_instance__analysis__project': _('parent'.capitalize() + ' project'),
            '-risk_instance__analysis__project': _('Parent project (descending)'),
            'solution': _('solution'.capitalize()),
            '-solution': _('Solution (descending)'),
        }
    )

    class Meta:
        model = Mitigation
        fields = ['title', 'type', 'risk_instance__analysis__project', 'solution']

class RiskAcceptanceFilter(GenericFilterSet):
    risk_instance__title = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search acceptance...')
        }
    ))
    type = GenericChoiceFilter(choices=RiskAcceptance.ACCEPTANCE_TYPE)
    orderby = GenericOrderingFilter(
        fields=(
            ('risk_instance__title', 'risk_instance__title'),
            ('type', 'type'),
            ('expiry_date', 'expiry_date'),
            ('validator', 'validator'),
        ),
        field_labels={
            'risk_instance__title': _('title'.capitalize()),
            '-risk_instance__title': _('Title (descending)'),
            'type': _('type'.capitalize()),
            '-type': _('Type (descending)'),
            'expiry_date': _('expiry'.capitalize() + ' date'),
            '-expiry_date': _('Expiry date (descending)'),
            'validator': _('validator'.capitalize()),
            '-validator': _('Validator (descending)'),
        }
    )

    class Meta:
        model = RiskAcceptance
        fields = ['risk_instance__title', 'type']

class ProjectsDomainFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search domain...')
        }
    ))
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('department', 'department'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'department': _('department'.capitalize()),
            '-department': _('Department (descending)'),
        }
    )
    class Meta:
        model = ProjectsGroup
        fields = ['name', 'department']

class ProjectFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search project...')
        }
    ))
    parent_group = GenericModelMultipleChoiceFilter(queryset=ProjectsGroup.objects.all())
    lc_status = GenericMultipleChoiceFilter(choices=Project.PRJ_LC_STATUS)
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('lc_status', 'lc_status'),
            ('parent_group', 'parent_group'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'lc_status': _('status'.capitalize()),
            '-lc_status': _('Status (descending)'),
            'parent_group': _('Parent domain'),
            '-parent_group': _('Parent domain (descending)'),
        }
    )

    class Meta:
        model = Project
        fields = '__all__'

class ThreatFilter(GenericFilterSet):
    title = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search threat...')
        }
    ))
    orderby = GenericOrderingFilter(
        fields=(
            ('title', 'title'),
        ),
        field_labels={
            'title': _('title'.capitalize()),
            '-title': _('Title'),
        }
    )

    class Meta:
        model = ParentRisk
        fields = '__all__'

class SecurityFunctionFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search function...')
        }
    ))
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('provider', 'provider'),
            ('contact', 'contact'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'provider': _('provider'.capitalize()),
            '-provider': _('Provider (descending)'),
            'contact': _('contact'.capitalize()),
            '-contact': _('Contact (descending)'),
        }
    )

    class Meta:
        model = Solution
        fields = '__all__'

class AssetFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search asset...')
        }
    ))
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
        }
    )

    class Meta:
        model = Asset
        fields = '__all__'
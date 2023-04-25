from django.forms import CharField, CheckboxInput, ChoiceField, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, CheckboxSelectMultiple, TextInput, Textarea, TimeInput, URLInput, widgets
from django_filters import FilterSet, OrderingFilter, ModelMultipleChoiceFilter, MultipleChoiceFilter, CharFilter, ChoiceFilter
# from django_filters.widgets import *
from django.db.models import Q

from core.models import Analysis, RiskScenario, SecurityMeasure, SecurityFunction, RiskAcceptance, RiskMatrix
from core.models import Asset, Folder, Project, Threat, SecurityFunction
from core.forms import SearchableSelect, SearchableCheckboxSelectMultiple
from iam.models import User, UserGroup, RoleAssignment
from django.utils.translation import gettext_lazy as _


class GenericFilterSet(FilterSet):
    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        # for f in self.filters.items():
        #     print(f[0], f[1].field.widget)


class GenericOrderingFilter(OrderingFilter):
    def __init__(self, *args, empty_label=_("Order by"), **kwargs):
        super().__init__(self, *args, empty_label=_("Order by"), widget=Select, **kwargs)
        self.field.widget.attrs = {
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'onchange': 'this.form.submit();'
        }


class GenericModelMultipleChoiceFilter(ModelMultipleChoiceFilter):
    widget = SearchableCheckboxSelectMultiple(
        attrs={
            'class': 'text-sm rounded',
            'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3',
            'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 overflow-y-scroll max-h-72'
        }
    )

    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


class GenericMultipleChoiceFilter(MultipleChoiceFilter):
    widget = SearchableCheckboxSelectMultiple(
        attrs={
            'class': 'text-sm rounded',
            'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3',
            'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 overflow-y-scroll max-h-72'
        }
    )

    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


class GenericCharFilter(CharFilter):
    widget = TextInput(
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
    widget = SearchableSelect(
        attrs={
            'class': 'text-sm rounded',
            'searchbar_class': '[&_.search-icon]:text-gray-500 text-sm px-3',
            'wrapper_class': 'border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll'
        }
    )

    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


def viewable_folders(request):
    if request is None:
        return Folder.objects.none()
    root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    accessible_folders = RoleAssignment.get_accessible_folders(
        root_folder, request.user, Folder.ContentType.DOMAIN
    )
    return Folder.objects.filter(id__in=accessible_folders)


class AnalysisFilter(GenericFilterSet):
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
    is_draft = GenericChoiceFilter(choices=STATUS_CHOICES, widget=Select(
        attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50'
        }
    ))
    auditor = GenericModelMultipleChoiceFilter(queryset=User.objects.filter(
        analysis__auditor__isnull=False).distinct(), label=('Auditor'))

    project__folder = GenericModelMultipleChoiceFilter(
        queryset=viewable_folders, label=_('Domain'))

    project = GenericModelMultipleChoiceFilter(queryset=Project.objects.all())

    class Meta:
        model = Analysis
        fields = ['is_draft', 'auditor', 'project']


class RiskScenarioFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search scenario...')
        }
    ))
    threat = GenericModelMultipleChoiceFilter(queryset=Threat.objects.all())
    analysis__project = GenericModelMultipleChoiceFilter(
        queryset=Project.objects.all(), label=_('Project'))
    analysis__project__folder = GenericModelMultipleChoiceFilter(
        queryset=viewable_folders, label=_('Domain'))
    treatment = GenericMultipleChoiceFilter(
        choices=RiskScenario.TREATMENT_OPTIONS)

    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('threat', 'threat'),
            ('analysis__project', 'analysis__project'),
            ('treatment', 'treatment'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'threat': _('threat'.capitalize()),
            '-threat': _('Threat (descending)'),
            'analysis__project': _('Project'),
            '-analysis__project': _('Project (descending)'),
            'treatment': _('treatment'.capitalize()),
            '-treatment': _('Treatment (descending)'),
        }
    )

    class Meta:
        model = RiskScenario
        fields = ['name', 'threat', 'analysis__project', 'treatment']


class SecurityMeasureFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search security measure...')
        }
    ))
    folder = GenericModelMultipleChoiceFilter(queryset=viewable_folders)
    type = GenericMultipleChoiceFilter(choices=SecurityMeasure.MITIGATION_TYPE)
    status = GenericMultipleChoiceFilter(
        choices=SecurityMeasure.MITIGATION_STATUS)
    security_function = GenericModelMultipleChoiceFilter(
        queryset=SecurityFunction.objects.all())

    orderby = GenericOrderingFilter(
        fields=(
            ('status', 'status'),
            ('name', 'name'),
            ('type', 'type'),
            ('folder', 'folder'),
            ('security_function', 'security_function'),
        ),
        field_labels={
            'status': _('status'.capitalize()),
            '-status': _('Status (descending)'),
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'type': _('type'.capitalize()),
            '-type': _('Type (descending)'),
            'folder': _('Domain'),
            '-folder': _('Domain (descending)'),
            'security_function': _('security function'.capitalize()),
            '-security_function': _('Security function (descending)'),
        }
    )

    class Meta:
        model = SecurityMeasure
        fields = ['name', 'type',
                  'folder', 'security_function']


class RiskAcceptanceFilter(GenericFilterSet):
    search = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search acceptance...')
        }
    ), method='acceptance_search')
    risk_scenarios = GenericModelMultipleChoiceFilter(
        queryset=RiskScenario.objects.filter(analysis__project__folder__content_type=Folder.ContentType.DOMAIN))
    folder = GenericModelMultipleChoiceFilter(queryset=viewable_folders)
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('risk_scenarios', 'risk_scenarios'),
            ('expiry_date', 'expiry_date'),
            ('validator', 'validator'),
            ('folder', 'folder'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'risk_scenarios': _('risk scenarios'.capitalize()),
            '-risk_scenarios': _('Risk scenarios (descending)'),
            'expiry_date': _('expiry'.capitalize() + ' date'),
            '-expiry_date': _('Expiry date (descending)'),
            'validator': _('validator'.capitalize()),
            '-validator': _('Validator (descending)'),
            'folder': _('Domain'.capitalize()),
            '-folder': _('Domain (descending)'),
        }
    )

    class Meta:
        model = RiskAcceptance
        fields = ['risk_scenarios', 'folder']

    def acceptance_search(self, queryset, name, search_query):
        return queryset.filter(
            Q(name__icontains=search_query) | Q(
                risk_scenarios__name__icontains=search_query)
        ).distinct()


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
            ('description', 'description'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'description': _('description'.capitalize()),
            '-description': _('Description (descending)'),
        }
    )

    class Meta:
        model = Folder
        fields = ['name', 'description']


class RiskMatrixFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search matrices...')
        }
    ))
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('description', 'description'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'description': _('description'.capitalize()),
            '-description': _('Description (descending)'),
        }
    )

    class Meta:
        model = RiskMatrix
        fields = ['name', 'description']


class ProjectFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search project...')
        }
    ))
    folder = GenericModelMultipleChoiceFilter(queryset=viewable_folders)
    lc_status = GenericMultipleChoiceFilter(choices=Project.PRJ_LC_STATUS)
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('lc_status', 'lc_status'),
            ('folder', 'folder'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'lc_status': _('status'.capitalize()),
            '-lc_status': _('Status (descending)'),
            'folder': _('Domain'),
            '-folder': _('Domain (descending)'),
        }
    )

    class Meta:
        model = Project
        fields = '__all__'
        exclude = ['created_at']


class ThreatFilter(GenericFilterSet):
    PROVIDER_CHOICES = Threat.objects.values_list(
        'provider', 'provider').distinct()

    name = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search threat...')
        }
    ))
    provider = GenericMultipleChoiceFilter(choices=PROVIDER_CHOICES)
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('provider', 'provider'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'provider': _('provider'.capitalize()),
            '-provider': _('Provider (descending)'),
        }
    )

    class Meta:
        model = Threat
        fields = '__all__'


class SecurityFunctionFilter(GenericFilterSet):
    PROVIDER_CHOICES = SecurityFunction.objects.exclude(
        provider__isnull=True).distinct('provider').values_list('provider', 'provider')

    name = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search function...')
        }
    ))
    provider = GenericMultipleChoiceFilter(
        choices=PROVIDER_CHOICES, null_label=_('None'))
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('provider', 'provider'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'provider': _('provider'.capitalize()),
            '-provider': _('Provider (descending)'),
        }
    )

    class Meta:
        model = SecurityFunction
        fields = '__all__'
        # TODO: is this necessary?
        exclude = ['created_at', 'folder', 'is_published']


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


class UserFilter(GenericFilterSet):

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']

    def user_search(queryset, name, value):
        return queryset.filter(
            Q(email__icontains=value) | Q(
                first_name__icontains=value) | Q(last_name__icontains=value)
        ).order_by('-is_active', '-is_superuser', 'email', 'id')

    YES_NO_CHOICES = (
        (True, _('Yes')),
        (False, _('No')),
    )

    is_superuser = GenericChoiceFilter(choices=YES_NO_CHOICES)
    is_active = GenericChoiceFilter(choices=YES_NO_CHOICES)

    user_groups = GenericModelMultipleChoiceFilter(
        queryset=UserGroup.objects.all())

    q = GenericCharFilter(method=user_search, label="Search", widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search user...')
        }))

    orderby = GenericOrderingFilter(
        fields=(
            ('email', 'email'),
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
            ('date_joined', 'date_joined')
        ),
        field_labels={
            'email': _('Email'),
            '-email': _('Email (descending)'),
            'first_name': _('First name'),
            '-first_name': _('First name (descending)'),
            'last_name': _('Last name'),
            '-last_name': _('Last name (descending)'),
            'date_joined': _('Created at'),
            '-date_joined': _('Created at (descending)')
        }
    )


class UserGroupFilter(GenericFilterSet):

    class Meta:
        model = UserGroup
        fields = '__all__'

    name = GenericCharFilter(widget=TextInput(
        attrs={
            'class': 'h-10 rounded-r-lg border-none focus:ring-0',
            'placeholder': _('Search user group...')
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

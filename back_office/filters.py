from django.forms import CharField, CheckboxInput, ChoiceField, DateInput, DateTimeInput, EmailInput, HiddenInput, ModelForm, NullBooleanSelect, NumberInput, PasswordInput, Select, SelectMultiple, TextInput, Textarea, TimeInput, URLInput, widgets
from django_filters import FilterSet, OrderingFilter, ModelMultipleChoiceFilter, MultipleChoiceFilter, CharFilter, ChoiceFilter
# from django_filters.widgets import *
from django.db.models import Q

from core.models import Analysis, RiskScenario, SecurityMeasure, SecurityFunction, RiskAcceptance
from general.models import Asset, Folder, Project, Threat, SecurityFunction
from general.models import Threat, Project
from iam.models import User, UserGroup
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
        try:
            for user in users:
                full_names += (user.id, user.get_full_name),
        except Exception as e:
            print(f"WORKAROUND: {e}")
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
    threat = GenericModelMultipleChoiceFilter(queryset=Threat.objects.all())
    analysis__project = GenericModelMultipleChoiceFilter(queryset=Project.objects.all())
    treatment = GenericMultipleChoiceFilter(choices=RiskScenario.TREATMENT_OPTIONS)

    orderby = GenericOrderingFilter(
        fields=(
            ('title', 'title'),
            ('threat', 'threat'),
            ('analysis__project', 'analysis__project'),
            ('treatment', 'treatment'),
        ),
        field_labels={
            'title': _('title'.capitalize()),
            '-title': _('Title (descending)'),
            'threat': _('threat'.capitalize()),
            '-threat': _('Threat (descending)'),
            'analysis__project': _('parent'.capitalize() + ' project'),
            '-analysis__project': _('Parent project (descending)'),
            'treatment': _('treatment'.capitalize()),
            '-treatment': _('Treatment (descending)'),
        }
    )

    class Meta:
        model = RiskScenario
        fields = ['title', 'threat', 'analysis__project', 'treatment']

class SecurityMeasureFilter(GenericFilterSet):
    title = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search security measure...')
        }
    ))
    risk_scenario__analysis__project = GenericModelMultipleChoiceFilter(queryset=Project.objects.all())
    type=GenericMultipleChoiceFilter(choices=SecurityMeasure.MITIGATION_TYPE)
    status=GenericMultipleChoiceFilter(choices=SecurityMeasure.MITIGATION_STATUS)
    security_function=GenericModelMultipleChoiceFilter(queryset=SecurityFunction.objects.all())

    orderby = GenericOrderingFilter(
        fields=(
            ('status', 'status'),
            ('title', 'title'),
            ('type', 'type'),
            ('risk_scenario__analysis__project', 'risk_scenario__analysis__project'),
            ('security_function', 'security_function'),
        ),
        field_labels={
            'status': _('status'.capitalize()),
            '-status': _('Status (descending)'),
            'title': _('title'.capitalize()),
            '-title': _('Title (descending)'),
            'type': _('type'.capitalize()),
            '-type': _('Type (descending)'),
            'risk_scenario__analysis__project': _('parent'.capitalize() + ' project'),
            '-risk_scenario__analysis__project': _('Parent project (descending)'),
            'security_function': _('security_function'.capitalize()),
            '-security_function': _('SecurityFunction (descending)'),
        }
    )

    class Meta:
        model = SecurityMeasure
        fields = ['title', 'type', 'risk_scenario__analysis__project', 'security_function']

class RiskAcceptanceFilter(GenericFilterSet):
    risk_scenario__title = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search acceptance...')
        }
    ))
    type = GenericChoiceFilter(choices=RiskAcceptance.ACCEPTANCE_TYPE)
    orderby = GenericOrderingFilter(
        fields=(
            ('risk_scenario__title', 'risk_scenario__title'),
            ('type', 'type'),
            ('expiry_date', 'expiry_date'),
            ('validator', 'validator'),
        ),
        field_labels={
            'risk_scenario__title': _('title'.capitalize()),
            '-risk_scenario__title': _('Title (descending)'),
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
        fields = ['risk_scenario__title', 'type']

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

class ProjectFilter(GenericFilterSet):
    name = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search project...')
        }
    ))
    folder = GenericModelMultipleChoiceFilter(queryset=Folder.objects.all())
    lc_status = GenericMultipleChoiceFilter(choices=Project.PRJ_LC_STATUS)
    orderby = GenericOrderingFilter(
        fields=(
            ('name', 'name'),
            ('lc_status', 'lc_status'),
            ('domain', 'domain'),
        ),
        field_labels={
            'name': _('name'.capitalize()),
            '-name': _('Name (descending)'),
            'lc_status': _('status'.capitalize()),
            '-lc_status': _('Status (descending)'),
            'domain': _('Parent domain'),
            '-domain': _('Parent domain (descending)'),
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
            '-title': _('Title (descending)'),
        }
    )

    class Meta:
        model = Threat
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
        model = SecurityFunction
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

class UserFilter(GenericFilterSet):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def user_search(queryset, name, value):
        return queryset.filter(
            Q(username__icontains=value) | Q(first_name__icontains=value) | Q(last_name__icontains=value)
        ).order_by('-is_active', '-is_superuser', 'username', 'id')

    YES_NO_CHOICES = (
        (True, _('Yes')),
        (False, _('No')),
    )

    is_superuser = GenericChoiceFilter(choices=YES_NO_CHOICES)
    is_active = GenericChoiceFilter(choices=YES_NO_CHOICES)

    groups = GenericModelMultipleChoiceFilter(queryset=UserGroup.objects.all())
    
    q = GenericCharFilter(method=user_search, label="Search", widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search user...')
        }))

    orderby = GenericOrderingFilter(
        fields=(
            ('username', 'username'),
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
            ('email', 'email'),
        ),
        field_labels={
            'username': _('username'.capitalize()),
            '-username': _('Username (descending)'),
            'first_name': _('First name'),
            '-first_name': _('First name (descending)'),
            'last_name': _('Last name'),
            '-last_name': _('Last name (descending)'),
            'email': _('Email address'),
            '-email': _('Email address (descending)'),
        }
    )

class UserGroupFilter(GenericFilterSet):

    class Meta:
        model = UserGroup
        fields = '__all__'

    name = GenericCharFilter(widget=TextInput(
        attrs={
                'class': 'h-10 rounded-r-lg border-none focus:ring-0',
                'placeholder': _('Search group...')
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
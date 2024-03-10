from django.forms import (
    Select,
    TextInput,
)
from django_filters import (
    FilterSet,
    OrderingFilter,
    ModelMultipleChoiceFilter,
    MultipleChoiceFilter,
    CharFilter,
    ChoiceFilter,
)
from django.db.models import Q

from core.models import *
from core.forms import SearchableSelect, SearchableCheckboxSelectMultiple
from iam.models import User, UserGroup, RoleAssignment, Folder
from core.models import Project, Threat, ReferenceControl, AppliedControl
from django.utils.translation import gettext_lazy as _


class GenericFilterSet(FilterSet):
    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        # for f in self.filters.items():
        #     print(f[0], f[1].field.widget)


class GenericOrderingFilter(OrderingFilter):
    def __init__(self, *args, empty_label=_("Order by"), **kwargs):
        super().__init__(
            self, *args, empty_label=_("Order by"), widget=Select, **kwargs
        )
        self.field.widget.attrs = {
            "class": "h-10 rounded-r-lg border-none focus:ring-0",
            "onchange": "this.form.submit();",
        }


class GenericModelMultipleChoiceFilter(ModelMultipleChoiceFilter):
    widget = SearchableCheckboxSelectMultiple(
        attrs={
            "class": "text-sm rounded",
            "searchbar_class": "[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3",
            "wrapper_class": "border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 overflow-y-scroll max-h-72",
        }
    )

    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


class GenericMultipleChoiceFilter(MultipleChoiceFilter):
    widget = SearchableCheckboxSelectMultiple(
        attrs={
            "class": "text-sm rounded",
            "searchbar_class": "[&_.search-icon]:text-gray-500 text-sm border border-gray-300 rounded-t-lg px-3",
            "wrapper_class": "border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 py-2 px-4 overflow-y-scroll max-h-72",
        }
    )

    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


class GenericCharFilter(CharFilter):
    widget = TextInput(attrs={"class": "h-10 rounded-r-lg border-none focus:ring-0"})

    def __init__(
        self,
        field_name=None,
        lookup_expr="icontains",
        *,
        label=None,
        method=None,
        distinct=False,
        exclude=False,
        widget=widget,
        search_term=None,
        **kwargs,
    ):
        super().__init__(
            field_name,
            lookup_expr="icontains",
            label=label,
            method=method,
            distinct=distinct,
            exclude=exclude,
            widget=widget,
            **kwargs,
        )
        placeholder = f"Search {search_term if search_term else ''}..."
        self.widget.attrs["placeholder"] = placeholder


class GenericChoiceFilter(ChoiceFilter):
    widget = SearchableSelect(
        attrs={
            "class": "text-sm rounded",
            "searchbar_class": "[&_.search-icon]:text-gray-500 text-sm px-3",
            "wrapper_class": "border border-gray-300 bg-gray-50 text-gray-900 text-sm rounded-b-lg focus:ring-blue-500 focus:border-blue-500 max-h-56 overflow-y-scroll",
        }
    )

    def __init__(self, *args, widget=widget, **kwargs):
        super().__init__(*args, widget=widget, **kwargs)


def viewable_folders(request):
    if request is None:
        return Folder.objects.none()
    accessible_folders = RoleAssignment.get_accessible_folders(
        Folder.get_root_folder(), request.user, Folder.ContentType.DOMAIN
    )
    return Folder.objects.filter(id__in=accessible_folders)


class AppliedControlFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search applied control..."),
            }
        )
    )
    folder = GenericModelMultipleChoiceFilter(queryset=viewable_folders)
    reference_control = GenericModelMultipleChoiceFilter(
        queryset=ReferenceControl.objects.all()
    )

    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("folder", "folder"),
            ("reference_control", "reference_control"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "folder": _("Domain"),
            "-folder": _("Domain (descending)"),
            "reference_control": _("reference control".capitalize()),
            "-reference_control": _("Reference control (descending)"),
        },
    )

    class Meta:
        model = AppliedControl
        fields = ["name", "folder", "reference_control"]


class ProjectsDomainFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search domain..."),
            }
        )
    )
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("description", "description"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "description": _("description".capitalize()),
            "-description": _("Description (descending)"),
        },
    )

    class Meta:
        model = Folder
        fields = ["name", "description"]


class ProjectFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search project..."),
            }
        )
    )
    folder = GenericModelMultipleChoiceFilter(queryset=viewable_folders)
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("folder", "folder"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "folder": _("Domain"),
            "-folder": _("Domain (descending)"),
        },
    )

    class Meta:
        model = Project
        fields = "__all__"
        exclude = ["created_at", "locale_data"]


class ThreatFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search threat..."),
            }
        )
    )
    orderby = GenericOrderingFilter(
        fields=(("name", "name"),),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
        },
    )

    class Meta:
        model = Threat
        fields = ["name"]


class ReferenceControlFilter(GenericFilterSet):
    PROVIDER_CHOICES = (
        ReferenceControl.objects.exclude(provider__isnull=True)
        .values_list("provider", "provider")
        .distinct()
    )

    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search function..."),
            }
        )
    )
    provider = GenericMultipleChoiceFilter(choices=PROVIDER_CHOICES, null_label="--")
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("provider", "provider"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "provider": _("provider".capitalize()),
            "-provider": _("Provider (descending)"),
        },
    )

    class Meta:
        model = ReferenceControl
        fields = ["provider"]


class UserFilter(GenericFilterSet):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]

    def user_search(queryset, name, value):
        return queryset.filter(
            Q(email__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
        ).order_by("-is_active", "-is_superuser", "email", "id")

    YES_NO_CHOICES = (
        (True, _("Yes")),
        (False, _("No")),
    )

    is_superuser = GenericChoiceFilter(
        choices=YES_NO_CHOICES,
        widget=Select(
            attrs={
                "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50"
            }
        ),
    )
    is_active = GenericChoiceFilter(
        choices=YES_NO_CHOICES,
        widget=Select(
            attrs={
                "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 disabled:opacity-50"
            }
        ),
    )

    user_groups = GenericModelMultipleChoiceFilter(queryset=UserGroup.objects.all())

    q = GenericCharFilter(
        method=user_search,
        label="Search",
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search user..."),
            }
        ),
    )

    orderby = GenericOrderingFilter(
        fields=(
            ("email", "email"),
            ("first_name", "first_name"),
            ("last_name", "last_name"),
            ("date_joined", "date_joined"),
        ),
        field_labels={
            "email": _("Email"),
            "-email": _("Email (descending)"),
            "first_name": _("First name"),
            "-first_name": _("First name (descending)"),
            "last_name": _("Last name"),
            "-last_name": _("Last name (descending)"),
            "date_joined": _("Created at"),
            "-date_joined": _("Created at (descending)"),
        },
    )


class UserGroupFilter(GenericFilterSet):
    class Meta:
        model = UserGroup
        fields = "__all__"

    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search user group..."),
            }
        )
    )

    orderby = GenericOrderingFilter(
        fields=(("name", "name"),),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
        },
    )


class ComplianceAssessmentFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search compliance assessment..."),
            }
        )
    )
    project = GenericModelMultipleChoiceFilter(queryset=Project.objects.all())
    framework = GenericModelMultipleChoiceFilter(queryset=Framework.objects.all())
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("description", "description"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "description": _("description".capitalize()),
            "-description": _("Description (descending)"),
        },
    )

    class Meta:
        model = ComplianceAssessment
        fields = "__all__"
        exclude = ["created_at", "locale_data"]


class RequirementAssessmentFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search requirement assessment..."),
            }
        )
    )
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("description", "description"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "description": _("description".capitalize()),
            "-description": _("Description (descending)"),
        },
    )

    class Meta:
        model = RequirementAssessment
        fields = ["name"]


class RequirementFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search requirement..."),
            }
        )
    )
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("description", "description"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "description": _("description".capitalize()),
            "-description": _("Description (descending)"),
        },
    )

    class Meta:
        model = RequirementNode
        fields = ["name"]


class EvidenceFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search evidence..."),
            }
        )
    )
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("description", "description"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "description": _("description".capitalize()),
            "-description": _("Description (descending)"),
        },
    )

    class Meta:
        model = Evidence
        fields = ["name"]


class FrameworkFilter(GenericFilterSet):
    name = GenericCharFilter(
        widget=TextInput(
            attrs={
                "class": "h-10 rounded-r-lg border-none focus:ring-0",
                "placeholder": _("Search framework..."),
            }
        )
    )
    orderby = GenericOrderingFilter(
        fields=(
            ("name", "name"),
            ("description", "description"),
        ),
        field_labels={
            "name": _("name".capitalize()),
            "-name": _("Name (descending)"),
            "description": _("description".capitalize()),
            "-description": _("Description (descending)"),
        },
    )

    class Meta:
        model = Framework
        fields = ["name"]

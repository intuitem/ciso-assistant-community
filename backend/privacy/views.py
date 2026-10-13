import io
import re
import uuid

import pandas as pd

from core.constants import COUNTRY_CHOICES
from core.models import Actor, Terminology, ValidationFlow
from core.serializers import ActorReadSerializer
from core.views import (
    BaseModelViewSet as AbstractBaseModelViewSet,
    ExportMixin,
    actor_prefetch,
    escape_excel_formula,
)
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Case, Count, F, Prefetch, Q, When
from itertools import chain
from collections import defaultdict

from core.utils import camel_case
from iam.models import Folder, RoleAssignment

from .models import (
    Purpose,
    PersonalData,
    DataSubject,
    DataRecipient,
    DataContractor,
    DataTransfer,
    Processing,
    RightRequest,
    DataBreach,
    DpiaRequirementChange,
    DpiaRequirementSource,
    ART6_LAWFUL_BASIS_CHOICES,
    ART9_SPECIAL_CATEGORY_CONDITION_CHOICES,
    TRANSFER_MECHANISM_CHOICES,
)

DPIA_OVERVIEW_PAGE = 50

EU_COUNTRIES_SET = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
}


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "privacy.serializers"


class PurposeViewSet(BaseModelViewSet):
    """
    API endpoint that allows purposes to be viewed or edited.
    """

    model = Purpose
    filterset_fields = ["processing", "legal_basis", "article_9_condition"]

    @action(detail=False, name="Get legal basis choices")
    def legal_basis(self, request):
        return Response(dict(ART6_LAWFUL_BASIS_CHOICES))

    @action(detail=False, name="Get article 9 condition choices")
    def article_9_condition(self, request):
        return Response(dict(ART9_SPECIAL_CATEGORY_CONDITION_CHOICES))


class PersonalDataViewSet(BaseModelViewSet):
    """
    API endpoint that allows personal data to be viewed or edited.
    """

    model = PersonalData
    filterset_fields = ["processing", "category", "assets"]

    @action(detail=False, name="Get deletion policy choices")
    def deletion_policy(self, request):
        return Response(dict(PersonalData.DELETION_POLICY_CHOICES))

    @action(detail=False, name="Get is_sensitive choices")
    def is_sensitive(self, request):
        return Response({"true": "Yes", "false": "No"})

    @action(detail=False, methods=["post"], url_path="batch-create")
    def batch_create(self, request):
        """
        Batch create multiple personal data entries for a processing.
        Expected format:
        {
            "processing": "uuid",
            "categories": ["privacy_name", "privacy_email", ...],
            "retention": "2 years",
            "deletion_policy": "privacy_automatic_deletion",
            "is_sensitive": false
        }
        """
        processing_id = request.data.get("processing")
        categories = request.data.get("categories", [])
        retention = request.data.get("retention", "")
        deletion_policy = request.data.get("deletion_policy", "")
        is_sensitive = request.data.get("is_sensitive", False)

        if not processing_id:
            return Response(
                {"error": "processing is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(categories, list) or not categories:
            return Response(
                {"error": "categories is required and must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Deduplicate while preserving order
        categories = list(dict.fromkeys(categories))

        try:
            processing_uuid = uuid.UUID(str(processing_id))
        except ValueError, AttributeError:
            return Response(
                {"error": "Invalid processing ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        viewable_ids = RoleAssignment.get_viewable_object_ids(request.user, Processing)
        try:
            processing = Processing.objects.filter(id__in=viewable_ids).get(
                id=processing_uuid
            )
        except Processing.DoesNotExist:
            return Response(
                {"error": "Processing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        category_terms = {
            str(t.id): t
            for t in Terminology.objects.filter(
                field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY,
                is_visible=True,
            )
        }
        valid_deletion_policies = {c[0] for c in PersonalData.DELETION_POLICY_CHOICES}

        if deletion_policy and deletion_policy not in valid_deletion_policies:
            return Response(
                {"error": f"Invalid deletion_policy: {deletion_policy}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_categories = {
            str(c)
            for c in PersonalData.objects.filter(processing=processing).values_list(
                "category", flat=True
            )
        }

        created_items = []
        skipped_items = []
        errors = []

        for category in categories:
            category = str(category)
            term = category_terms.get(category)
            if term is None:
                errors.append({"category": category, "error": "Invalid category"})
                continue

            if category in existing_categories:
                existing = PersonalData.objects.filter(
                    processing=processing, category=term
                ).first()
                if existing:
                    skipped_items.append(
                        {
                            "id": str(existing.id),
                            "category": str(existing.category),
                            "name": str(existing),
                        }
                    )
                continue

            pd = PersonalData.objects.create(
                processing=processing,
                category=term,
                retention=retention,
                deletion_policy=deletion_policy,
                is_sensitive=is_sensitive,
            )
            created_items.append(
                {
                    "id": str(pd.id),
                    "category": str(pd.category),
                    "name": str(pd),
                }
            )

        return Response(
            {
                "success": True,
                "created": len(created_items),
                "skipped": len(skipped_items),
                "personal_data": created_items,
                "skipped_personal_data": skipped_items,
                "errors": errors,
            },
            status=status.HTTP_201_CREATED if created_items else status.HTTP_200_OK,
        )


class DataSubjectViewSet(BaseModelViewSet):
    """
    API endpoint that allows data subjects to be viewed or edited.
    """

    model = DataSubject
    filterset_fields = ["processing"]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(DataSubject.CATEGORY_CHOICES))


class DataRecipientViewSet(BaseModelViewSet):
    """
    API endpoint that allows data recipients to be viewed or edited.
    """

    model = DataRecipient
    filterset_fields = ["processing"]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(DataRecipient.CATEGORY_CHOICES))


class DataContractorViewSet(BaseModelViewSet):
    """
    API endpoint that allows data contractors to be viewed or edited.
    """

    model = DataContractor
    filterset_fields = ["processing"]

    @action(detail=False, name="Get category choices")
    def relationship_type(self, request):
        return Response(dict(DataContractor.RELATIONSHIP_TYPE_CHOICES))

    # this should be cached
    @action(detail=False, name="Get countries list")
    def country(self, request):
        return Response(dict(COUNTRY_CHOICES))


class DataTransferViewSet(BaseModelViewSet):
    """
    API endpoint that allows data transfers to be viewed or edited.
    """

    model = DataTransfer
    filterset_fields = ["processing", "transfer_mechanism"]

    # this should be cached
    @action(detail=False, name="Get countries list")
    def country(self, request):
        return Response(dict(COUNTRY_CHOICES))

    @action(detail=False, name="Get transfer mechanism choices")
    def transfer_mechanism(self, request):
        return Response(dict(TRANSFER_MECHANISM_CHOICES))


def agg_countries(viewable_data_transfers, viewable_data_contractors):
    transfer_countries = (
        DataTransfer.objects.filter(id__in=viewable_data_transfers)
        .values("country")
        .annotate(count=Count("id"))
    )
    contractor_countries = (
        DataContractor.objects.filter(id__in=viewable_data_contractors)
        .values("country")
        .annotate(count=Count("id"))
    )
    country_counts = defaultdict(int)
    for item in chain(transfer_countries, contractor_countries):
        country_counts[item["country"]] += item["count"]

    # if country code is in EU (GDPR scope) set the dict color to #A7CC74 otherwise to #F4B83D
    countries = [
        {
            "id": country,
            "count": count,
            "color": "#A7CC74" if country in EU_COUNTRIES_SET else "#F4B83D",
        }
        for country, count in country_counts.items()
    ]

    return countries


class ProcessingViewSet(ExportMixin, BaseModelViewSet):
    model = Processing

    filterset_fields = [
        "folder",
        "nature",
        "status",
        "filtering_labels",
        "assigned_to",
        "perimeters",
        "personal_data__category",
        "data_subjects__category",
        "dpia_required",
        "dpia_required_source",
    ]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("folder", "dpia_screening")
            .prefetch_related(
                "personal_data__category",
                "data_subjects",
                "nature",
                "associated_controls",
                actor_prefetch("assigned_to"),
                "evidences",
                "purposes",
                "perimeters",
                Prefetch(
                    "validationflow_set",
                    queryset=ValidationFlow.objects.select_related("approver"),
                ),
            )
        )

    export_config = {
        "fields": {
            "internal_id": {"source": "id", "label": "internal_id"},
            "ref_id": {"source": "ref_id", "label": "ref_id", "escape": True},
            "name": {"source": "name", "label": "name", "escape": True},
            "description": {
                "source": "description",
                "label": "description",
                "escape": True,
            },
            "status": {"source": "get_status_display", "label": "status"},
            "nature": {
                "source": "nature",
                "label": "processing_nature",
                "format": lambda qs: ",".join(
                    escape_excel_formula(str(n)) for n in qs.all()
                ),
            },
            "folder": {"source": "folder.name", "label": "folder", "escape": True},
            "assigned_to": {
                "source": "assigned_to",
                "label": "assigned_to",
                "format": lambda qs: ",".join(
                    escape_excel_formula(str(actor)) for actor in qs.all()
                ),
            },
            "labels": {
                "source": "filtering_labels",
                "label": "labels",
                "format": lambda qs: ",".join(
                    escape_excel_formula(o.label) for o in qs.all()
                ),
            },
            "dpia_required": {"source": "dpia_required", "label": "dpia_required"},
            "dpia_reference": {
                "source": "dpia_reference",
                "label": "dpia_reference",
                "escape": True,
            },
        },
        "filename": "processings_export",
        "select_related": ["folder"],
        "prefetch_related": ["filtering_labels", "nature", "assigned_to"],
    }

    @action(
        detail=True,
        methods=["get"],
        url_path="export-xlsx",
        name="Export processing as XLSX",
    )
    def export_record_xlsx(self, request, pk):
        processing = self.get_object()

        def txt(value):
            return escape_excel_formula(value) if isinstance(value, str) else value

        processing_rows = [
            {
                "ref_id": txt(processing.ref_id),
                "name": txt(processing.name),
                "description": txt(processing.description or ""),
                "domain": txt(processing.folder.name),
                "status": processing.status,
                "processing_nature": ",".join(
                    txt(n.name) for n in processing.nature.all()
                ),
                "information_channel": txt(processing.information_channel),
                "usage_channel": txt(processing.usage_channel),
                "dpia_required": processing.dpia_required,
                "dpia_reference": txt(processing.dpia_reference),
                "assigned_to": ",".join(
                    txt(a.user.email if a.user else str(a))
                    for a in processing.assigned_to.all()
                ),
                "labels": ",".join(
                    txt(label.label) for label in processing.filtering_labels.all()
                ),
            }
        ]

        sheets = [
            ("Processing", list(processing_rows[0].keys()), processing_rows),
            (
                "Purposes",
                ["name", "description", "legal_basis", "article_9_condition"],
                [
                    {
                        "name": txt(purpose.name or ""),
                        "description": txt(purpose.description or ""),
                        "legal_basis": purpose.legal_basis,
                        "article_9_condition": purpose.article_9_condition or "",
                    }
                    for purpose in processing.purposes.all()
                ],
            ),
            (
                "Personal data",
                [
                    "name",
                    "description",
                    "category",
                    "retention",
                    "deletion_policy",
                    "is_sensitive",
                    "assets",
                ],
                [
                    {
                        "name": txt(item.name or ""),
                        "description": txt(item.description or ""),
                        "category": txt(item.category.name),
                        "retention": txt(item.retention),
                        "deletion_policy": item.deletion_policy,
                        "is_sensitive": item.is_sensitive,
                        "assets": ",".join(
                            txt(asset.name) for asset in item.assets.all()
                        ),
                    }
                    for item in processing.personal_data.select_related(
                        "category"
                    ).prefetch_related("assets")
                ],
            ),
            (
                "Data subjects",
                ["name", "description", "category"],
                [
                    {
                        "name": txt(subject.name or ""),
                        "description": txt(subject.description or ""),
                        "category": subject.category,
                    }
                    for subject in processing.data_subjects.all()
                ],
            ),
            (
                "Data recipients",
                ["name", "description", "category"],
                [
                    {
                        "name": txt(recipient.name or ""),
                        "description": txt(recipient.description or ""),
                        "category": recipient.category,
                    }
                    for recipient in processing.data_recipients.all()
                ],
            ),
            (
                "Contractors",
                [
                    "name",
                    "description",
                    "entity",
                    "relationship_type",
                    "country",
                    "documentation_link",
                ],
                [
                    {
                        "name": txt(contractor.name or ""),
                        "description": txt(contractor.description or ""),
                        "entity": txt(contractor.entity.name)
                        if contractor.entity
                        else "",
                        "relationship_type": contractor.relationship_type,
                        "country": contractor.country,
                        "documentation_link": txt(contractor.documentation_link),
                    }
                    for contractor in processing.contractors_involved.select_related(
                        "entity"
                    )
                ],
            ),
            (
                "Transfers",
                [
                    "name",
                    "description",
                    "entity",
                    "country",
                    "transfer_mechanism",
                    "guarantees",
                    "documentation_link",
                ],
                [
                    {
                        "name": txt(transfer.name or ""),
                        "description": txt(transfer.description or ""),
                        "entity": txt(transfer.entity.name) if transfer.entity else "",
                        "country": transfer.country,
                        "transfer_mechanism": transfer.transfer_mechanism,
                        "guarantees": txt(transfer.guarantees),
                        "documentation_link": txt(transfer.documentation_link),
                    }
                    for transfer in processing.data_transfers.select_related("entity")
                ],
            ),
        ]

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet_name, columns, rows in sheets:
                pd.DataFrame(rows, columns=columns).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )
        buffer.seek(0)

        slug = re.sub(
            r"[^A-Za-z0-9_-]+", "-", processing.ref_id or processing.name
        ).strip("-")[:60] or str(processing.id)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="processing-{slug}.xlsx"'
        )
        return response

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Processing.STATUS_CHOICES))

    @action(detail=False, name="Get all processing assigned_to actors")
    def assigned_to(self, request):
        return Response(
            ActorReadSerializer(
                Actor.objects.filter(assigned_processings__isnull=False).distinct(),
                many=True,
            ).data
        )

    @action(detail=False, name="Get DPIA requirement choices")
    def dpia_required(self, request):
        return Response({"true": _("DPIA required"), "false": _("No DPIA required")})

    @action(detail=False, name="Get DPIA requirement source choices")
    def dpia_required_source(self, request):
        return Response(dict(DpiaRequirementSource.choices))

    @action(detail=False, url_path="dpia-screening-forms", name="DPIA screening forms")
    def dpia_screening_forms(self, request):
        """Forms the caller can see whose accepted responses set a processing's
        DPIA requirement, with what keeps them from applying."""
        from core.models import QuickForm
        from core.quick_form_apply import on_accept_health

        viewable = RoleAssignment.get_viewable_object_ids(request.user, QuickForm)
        rows = []
        cache: dict = {}
        for quick_form in (
            QuickForm.objects.filter(id__in=viewable)
            .exclude(on_accept=[])
            .select_related("library")
            .order_by("name")
        ):
            health = next(
                (
                    h
                    for h in on_accept_health(quick_form, cache)
                    if h["target"] == "processing.dpia_required"
                ),
                None,
            )
            if health is None:
                continue
            rows.append(
                {
                    "id": str(quick_form.id),
                    "name": quick_form.get_name_translated,
                    "library": quick_form.library.name if quick_form.library else None,
                    "problems": health["problems"],
                }
            )
        return Response(rows)

    @action(detail=False, url_path="dpia-overview", name="DPIA overview")
    def dpia_overview(self, request):
        """Where the processings the caller can see stand on DPIAs: a count per
        state, and one page of processings (`state`, `search`, `offset`), each
        with its DPIA and any screening awaiting review."""
        from core.models import QuickFormResponse
        from core.quick_form_apply import forms_with_target

        viewable = Processing.objects.filter(
            id__in=RoleAssignment.get_viewable_object_ids(request.user, Processing)
        )
        open_statuses = [
            QuickFormResponse.Status.DRAFT,
            QuickFormResponse.Status.SUBMITTED,
            QuickFormResponse.Status.IN_REVIEW,
        ]
        on_processings = QuickFormResponse.objects.filter(
            subject_content_type=ContentType.objects.get_for_model(Processing)
        )
        required = viewable.filter(dpia_required=True)
        # Under way: a DPIA still open. A rejected one is no DPIA.
        open_dpias = on_processings.filter(
            quick_form__in=forms_with_target("processing.dpia"),
            status__in=open_statuses,
        )
        open_ids = open_dpias.values("subject_object_id")
        not_required = viewable.filter(dpia_required=False)
        # Screenings waiting on a reviewer, whatever form they came from.
        pending_screenings = on_processings.filter(
            quick_form__in=forms_with_target("processing.dpia_required"),
            status__in=[
                QuickFormResponse.Status.SUBMITTED,
                QuickFormResponse.Status.IN_REVIEW,
            ],
        )
        by_state = {
            # The to-do list: required, no DPIA of record and none under way.
            "required_without_dpia": required.filter(dpia__isnull=True).exclude(
                id__in=open_ids
            ),
            "required_dpia_in_progress": required.filter(
                dpia__isnull=True, id__in=open_ids
            ),
            # Done: an accepted DPIA is the processing's DPIA of record.
            "required_dpia_done": required.filter(dpia__isnull=False),
            "not_required": not_required.exclude(dpia_required_source=""),
            # Never set by a screening or by hand: the default `False`.
            "not_assessed": not_required.filter(dpia_required_source=""),
            "awaiting_review": viewable.filter(
                id__in=pending_screenings.values("subject_object_id")
            ),
        }
        counts = {key: rows.count() for key, rows in by_state.items()}

        rows = by_state.get(request.query_params.get("state", ""), viewable)
        search = request.query_params.get("search", "").strip()
        if search:
            rows = rows.filter(Q(name__icontains=search) | Q(ref_id__icontains=search))
        # Most urgent first; oldest requirement first, never dated (backfilled) leading.
        rows = rows.select_related("folder", "dpia").order_by(
            Case(
                When(dpia_required=True, dpia__isnull=True, then=0),
                When(dpia_required=True, then=1),
                When(dpia_required_source="", then=3),
                default=2,
            ),
            F("dpia_required_set_at").asc(nulls_first=True),
            "name",
        )
        try:
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except ValueError:
            offset = 0
        page = list(rows[offset : offset + DPIA_OVERVIEW_PAGE])

        # The responses each row links to, only those the caller may open.
        readable = set(
            RoleAssignment.get_viewable_object_ids(request.user, QuickFormResponse)
        )
        ids = [p.id for p in page]
        latest_open = {
            str(r.subject_object_id): r
            for r in open_dpias.filter(subject_object_id__in=ids).order_by("updated_at")
        }
        pending = {
            str(r.subject_object_id): r
            for r in pending_screenings.filter(subject_object_id__in=ids).order_by(
                "updated_at"
            )
        }

        def link(response):
            if response is None or response.id not in readable:
                return None
            return {
                "id": str(response.id),
                "ref_id": response.ref_id,
                "status": response.status,
                "resolution": response.resolution,
            }

        def state_of(p):
            if not p.dpia_required:
                return "not_required" if p.dpia_required_source else "not_assessed"
            if p.dpia_id:
                return "required_dpia_done"
            if str(p.id) in latest_open:
                return "required_dpia_in_progress"
            return "required_without_dpia"

        return Response(
            {
                "total": viewable.count(),
                **counts,
                "rows_count": rows.count(),
                "rows": [
                    {
                        "id": str(p.id),
                        "ref_id": p.ref_id,
                        "name": p.name,
                        "folder": p.folder.name,
                        "state": state_of(p),
                        "set_at": p.dpia_required_set_at,
                        "dpia": link(p.dpia or latest_open.get(str(p.id))),
                        "pending_screening": link(pending.get(str(p.id))),
                    }
                    for p in page
                ],
            }
        )

    @action(detail=False, name="processing metrics")
    def metrics(self, request, pk=None):
        return Response({})

    @action(detail=False, name="aggregated metrics")
    def agg_metrics(self, request):
        viewable_processings = RoleAssignment.get_viewable_object_ids(
            request.user, Processing
        )
        viewable_data_contractors = RoleAssignment.get_viewable_object_ids(
            request.user, DataContractor
        )
        viewable_data_transfers = RoleAssignment.get_viewable_object_ids(
            request.user, DataTransfer
        )
        viewable_right_requests = RoleAssignment.get_viewable_object_ids(
            request.user, RightRequest
        )
        viewable_data_breaches = RoleAssignment.get_viewable_object_ids(
            request.user, DataBreach
        )
        viewable_personal_data = RoleAssignment.get_viewable_object_ids(
            request.user, PersonalData
        )
        viewable_data_recipients = RoleAssignment.get_viewable_object_ids(
            request.user, DataRecipient
        )

        processings_count = len(viewable_processings)

        pd_categories = PersonalData.get_categories_count(
            filters={"id__in": viewable_personal_data}
        )
        total_categories = len(pd_categories)
        # Recipients count was previously the sum of distinct entities from data contractors and data transfers
        # contractor_entities = (
        #     DataContractor.objects.filter(
        #         id__in=viewable_data_contractors, entity__isnull=False
        #     )
        #     .values_list("entity", flat=True)
        #     .distinct()
        # )
        # transfer_entities = (
        #     DataTransfer.objects.filter(
        #         id__in=viewable_data_transfers, entity__isnull=False
        #     )
        #     .values_list("entity", flat=True)
        #     .distinct()
        # )
        recipients_count = len(viewable_data_recipients)

        open_right_requests_count = (
            RightRequest.objects.filter(id__in=viewable_right_requests)
            .exclude(status="done")
            .count()
        )
        open_data_breaches_count = (
            DataBreach.objects.filter(id__in=viewable_data_breaches)
            .exclude(status="privacy_closed")
            .count()
        )

        # Aggregate data breaches by breach type
        breach_type_labels = dict(DataBreach.BREACH_TYPE_CHOICES)
        breach_types = (
            DataBreach.objects.filter(id__in=viewable_data_breaches)
            .values("breach_type")
            .annotate(count=Count("id"))
        )
        breach_type_data = [
            {
                "name": breach_type_labels.get(
                    item["breach_type"], item["breach_type"]
                ),
                "localName": camel_case(item["breach_type"]),
                "value": item["count"],
            }
            for item in breach_types
        ]

        # Aggregate right requests by request type
        request_type_labels = dict(RightRequest.REQUEST_TYPE_CHOICES)
        request_types = (
            RightRequest.objects.filter(id__in=viewable_right_requests)
            .values("request_type")
            .annotate(count=Count("id"))
        )
        request_type_data = [
            {
                "name": request_type_labels.get(
                    item["request_type"], item["request_type"]
                ),
                "localName": camel_case(item["request_type"]),
                "value": item["count"],
            }
            for item in request_types
        ]

        # Build Sankey diagram data: Personal Data → Processing → Legal Basis
        sankey_nodes = []
        sankey_links = []
        node_indices = {}  # Map node names to indices

        # Get all personal data with their processings and legal bases
        personal_data = (
            PersonalData.objects.select_related("processing", "category")
            .prefetch_related("processing__purposes", "processing__data_transfers")
            .filter(id__in=viewable_personal_data)
        )

        for pd in personal_data:
            pd_category = pd.category.name
            processing_name = (
                pd.processing.name if pd.processing else "Unknown Processing"
            )

            # Add personal data category node (depth 0)
            pd_key = f"pd_{pd_category}"
            if pd_key not in node_indices:
                node_indices[pd_key] = len(sankey_nodes)
                sankey_nodes.append({"name": pd_category, "depth": 0})

            # Add processing node (depth 1)
            proc_key = f"proc_{processing_name}"
            if proc_key not in node_indices:
                node_indices[proc_key] = len(sankey_nodes)
                sankey_nodes.append(
                    {"name": f"Processing: {processing_name}", "depth": 1}
                )

            # Link personal data to processing
            existing_link = next(
                (
                    l
                    for l in sankey_links
                    if l["source"] == node_indices[pd_key]
                    and l["target"] == node_indices[proc_key]
                ),
                None,
            )
            if existing_link:
                existing_link["value"] += 1
            else:
                sankey_links.append(
                    {
                        "source": node_indices[pd_key],
                        "target": node_indices[proc_key],
                        "value": 1,
                    }
                )

            # Get legal bases from purposes (Art. 6 legal bases only)
            legal_bases = set()
            if pd.processing:
                for purpose in pd.processing.purposes.all():
                    if purpose.legal_basis:
                        legal_bases.add(purpose.legal_basis)

            # Link processing to legal bases (depth 2)
            for legal_basis in legal_bases:
                legal_key = f"legal_{legal_basis}"
                if legal_key not in node_indices:
                    node_indices[legal_key] = len(sankey_nodes)
                    sankey_nodes.append(
                        {"name": f"LegalBasis: {legal_basis}", "depth": 2}
                    )

                existing_link = next(
                    (
                        l
                        for l in sankey_links
                        if l["source"] == node_indices[proc_key]
                        and l["target"] == node_indices[legal_key]
                    ),
                    None,
                )
                if existing_link:
                    existing_link["value"] += 1
                else:
                    sankey_links.append(
                        {
                            "source": node_indices[proc_key],
                            "target": node_indices[legal_key],
                            "value": 1,
                        }
                    )

        return Response(
            {
                "countries": agg_countries(
                    viewable_data_transfers, viewable_data_contractors
                ),
                "processings_count": processings_count,
                "recipients_count": recipients_count,
                "pd_categories": pd_categories,
                "pd_cat_count": total_categories,
                "open_right_requests_count": open_right_requests_count,
                "open_data_breaches_count": open_data_breaches_count,
                "breach_types": breach_type_data,
                "request_types": request_type_data,
                "sankey_nodes": sankey_nodes,
                "sankey_links": sankey_links,
            }
        )


class RightRequestViewSet(BaseModelViewSet):
    """
    API endpoint that allows right requests to be viewed or edited.
    """

    model = RightRequest
    filterset_fields = [
        "name",
        "owner",
        "request_type",
        "status",
        "processings",
        "folder",
        "due_date",
    ]

    @action(detail=False, name="Get request type choices")
    def request_type(self, request):
        return Response(dict(RightRequest.REQUEST_TYPE_CHOICES))

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(RightRequest.STATUS_CHOICES))

    @action(detail=False, name="Get all right request owners")
    def owner(self, request):
        return Response(
            ActorReadSerializer(
                Actor.objects.filter(assigned_right_requests__isnull=False).distinct(),
                many=True,
            ).data
        )


class DataBreachViewSet(BaseModelViewSet):
    """
    API endpoint that allows data breaches to be viewed or edited.
    """

    model = DataBreach
    filterset_fields = [
        "name",
        "folder",
        "breach_type",
        "risk_level",
        "status",
        "authorities",
        "affected_processings",
        "incident",
        "evidences",
        "discovered_on",
        "authority_notified_on",
    ]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("folder", "incident")
            .prefetch_related(
                "assigned_to",
                "authorities",
                "affected_processings",
                "affected_personal_data",
                "remediation_measures",
                "evidences",
            )
        )

    def _process_incident(self, request) -> None:
        """Turn a name typed into the incident picker into an incident.

        Like the responsibility matrix of an EBIOS RM study: reuse an incident of
        that name the user can see in the breach's domain, otherwise create one
        there through its write serializer (add permission checked).
        """
        value = request.data.get("incident")
        if not value or not isinstance(value, str):
            return
        try:
            uuid.UUID(value)
            return
        except ValueError:
            pass
        from core.models import Incident
        from core.serializers import IncidentWriteSerializer

        folder_id = request.data.get("folder")
        if not folder_id and self.kwargs.get("pk"):
            folder_id = self.get_object().folder_id
        folder = Folder.objects.filter(id=folder_id).first()
        if folder is None:
            return
        incident = Incident.objects.filter(
            name=value,
            folder=folder,
            id__in=RoleAssignment.get_viewable_object_ids(request.user, Incident),
        ).first()
        if incident is None:
            serializer = IncidentWriteSerializer(
                data={"name": value, "folder": str(folder.id)},
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            incident = serializer.save()
        if hasattr(request.data, "_mutable"):
            request.data._mutable = True
        request.data["incident"] = str(incident.id)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            self._process_incident(request)
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            self._process_incident(request)
            return super().update(request, *args, **kwargs)

    @action(detail=False, name="Get breach type choices")
    def breach_type(self, request):
        return Response(dict(DataBreach.BREACH_TYPE_CHOICES))

    @action(detail=False, name="Get risk level choices")
    def risk_level(self, request):
        return Response(dict(DataBreach.RISK_LEVEL_CHOICES))

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(DataBreach.STATUS_CHOICES))


class DpiaRequirementChangeViewSet(BaseModelViewSet):
    """History of DPIA requirement changes. Written only by `set_dpia_required`."""

    model = DpiaRequirementChange
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["processing", "dpia_required", "source", "changed_by", "folder"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("processing", "response", "changed_by", "folder")
        )

    @action(detail=False, name="Get source choices")
    def source(self, request):
        return Response(dict(DpiaRequirementSource.choices))

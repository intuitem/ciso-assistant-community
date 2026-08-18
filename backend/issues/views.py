from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status as drf_status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet
from global_settings.models import GlobalSettings
from issues.models import CommitmentVersion, RemediationIssue
from issues.serializers import CommitmentVersionReadSerializer

LONG_CACHE_TTL = 60  # mn

TERMINAL_STATUSES = (
    RemediationIssue.Status.DONE,
    RemediationIssue.Status.CANCELLED,
)


def self_validation_allowed() -> bool:
    general = GlobalSettings.objects.filter(
        name=GlobalSettings.Names.GENERAL
    ).first()
    if general is None:
        return False
    return bool(general.value.get("allow_self_validation", False))


class RemediationIssueViewSet(BaseModelViewSet):
    model = RemediationIssue
    serializers_module = "issues.serializers"
    filterset_fields = [
        "folder",
        "status",
        "priority",
        "requirement_assessments",
        "findings",
        "evidences",
        "applied_controls",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(RemediationIssue.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get resolution choices")
    def resolution(self, request):
        return Response(dict(RemediationIssue.Resolution.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get cancellation reason choices")
    def cancellation_reason(self, request):
        return Response(dict(RemediationIssue.CancellationReason.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get priority choices")
    def priority(self, request):
        return Response(dict(RemediationIssue.PRIORITY))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get acceptance state choices")
    def acceptance(self, request):
        return Response(dict(RemediationIssue.AcceptanceState.choices))

    # -- commitment and transition actions ------------------------------------
    # Eligibility is representative membership on top of object visibility
    # (issues-engagements.md §10.3/§10.6/§13): the acting natural user must
    # resolve through a listed representative actor of the relevant side.

    def _error(self, key: str, http_status=drf_status.HTTP_400_BAD_REQUEST):
        return Response({"error": key}, status=http_status)

    def _resolve_side(self, issue: RemediationIssue, request):
        """The side the user acts for: the one they represent, or the one they
        chose when they represent both. None → an error response is returned."""
        represented = [
            side
            for side in (
                RemediationIssue.Side.LEAD,
                RemediationIssue.Side.RESPONDENT,
            )
            if issue.user_is_representative(request.user, side)
        ]
        if not represented:
            return None, self._error(
                "notARepresentative", drf_status.HTTP_403_FORBIDDEN
            )
        requested = request.data.get("side")
        if requested:
            if requested not in represented:
                return None, self._error(
                    "notARepresentative", drf_status.HTTP_403_FORBIDDEN
                )
            return requested, None
        if len(represented) == 1:
            return represented[0], None
        return None, self._error("sideRequired")

    def _self_validation_guard(self, issue: RemediationIssue, user, side: str):
        """When self-validation is disabled, the same natural user cannot perform
        commitment actions for both sides of one Issue (§10.5)."""
        if self_validation_allowed():
            return None
        acted = issue.sides_acted_by(user)
        if acted - {side}:
            return self._error("selfValidationNotAllowed")
        return None

    def _terminal_guard(self, issue: RemediationIssue):
        if issue.status in TERMINAL_STATUSES:
            return self._error("issueClosedReopenFirst")
        return None

    @action(detail=True, methods=["post"], name="Propose a commitment version")
    def propose_commitment(self, request, pk=None):
        issue = self.get_object()
        if error := self._terminal_guard(issue):
            return error
        side, error = self._resolve_side(issue, request)
        if error:
            return error
        if error := self._self_validation_guard(issue, request.user, side):
            return error

        text = (request.data.get("text") or "").strip()
        if not text:
            return self._error("commitmentTextRequired")
        due_date = request.data.get("due_date") or None

        current = issue.current_commitment
        based_on = request.data.get("based_on_version_id")
        based_on = str(based_on) if based_on else None
        current_id = str(current.id) if current else None
        if based_on != current_id:
            return Response(
                {
                    "error": "commitmentVersionConflict",
                    "current_version": CommitmentVersionReadSerializer(
                        current
                    ).data
                    if current
                    else None,
                },
                status=drf_status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                version = CommitmentVersion.objects.create(
                    issue=issue,
                    version_number=(current.version_number + 1) if current else 1,
                    text=text,
                    due_date=due_date,
                    author=request.user,
                    author_side=side,
                )
        except IntegrityError:
            # Concurrent proposal won the unique (issue, version_number) race.
            return Response(
                {
                    "error": "commitmentVersionConflict",
                    "current_version": CommitmentVersionReadSerializer(
                        issue.current_commitment
                    ).data,
                },
                status=drf_status.HTTP_409_CONFLICT,
            )
        return Response(
            CommitmentVersionReadSerializer(version).data,
            status=drf_status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], name="Set a side's acceptance state")
    def set_acceptance(self, request, pk=None):
        issue = self.get_object()
        if error := self._terminal_guard(issue):
            return error
        side, error = self._resolve_side(issue, request)
        if error:
            return error
        if error := self._self_validation_guard(issue, request.user, side):
            return error

        state = request.data.get("state")
        if state not in (
            RemediationIssue.AcceptanceState.ACCEPTED,
            RemediationIssue.AcceptanceState.CHANGES_REQUESTED,
        ):
            return self._error("invalidAcceptanceState")

        version = issue.current_commitment
        if version is None:
            return self._error("noCommitmentToAccept")

        state_field, user_field, at_field = version.acceptance_field_names(side)
        setattr(version, state_field, state)
        setattr(version, user_field, request.user)
        setattr(version, at_field, timezone.now())
        version.save()
        return Response(CommitmentVersionReadSerializer(version).data)

    @action(detail=True, methods=["post"], name="Submit remediation for review")
    def submit_review(self, request, pk=None):
        issue = self.get_object()
        if error := self._terminal_guard(issue):
            return error
        if not issue.user_is_representative(
            request.user, RemediationIssue.Side.RESPONDENT
        ):
            return self._error(
                "onlyRespondentRepresentative", drf_status.HTTP_403_FORBIDDEN
            )
        issue.status = RemediationIssue.Status.IN_REVIEW
        issue.save()
        return Response({"status": issue.status})

    @action(detail=True, methods=["post"], name="Close the issue")
    def close(self, request, pk=None):
        issue = self.get_object()
        if error := self._terminal_guard(issue):
            return error
        if not issue.user_is_representative(
            request.user, RemediationIssue.Side.LEAD
        ):
            return self._error(
                "onlyLeadRepresentative", drf_status.HTTP_403_FORBIDDEN
            )
        version = issue.current_commitment
        if version is None or not version.accepted:
            return self._error("commitmentNotAccepted")
        resolution = request.data.get("resolution")
        if resolution not in RemediationIssue.Resolution.values:
            return self._error("resolutionRequired")
        justification = (request.data.get("closure_justification") or "").strip()
        if not justification:
            return self._error("closureJustificationRequired")
        issue.status = RemediationIssue.Status.DONE
        issue.resolution = resolution
        issue.closure_justification = justification
        issue.closed_at = timezone.now()
        issue.save()
        return Response({"status": issue.status})

    @action(detail=True, methods=["post"], name="Cancel the issue")
    def cancel(self, request, pk=None):
        issue = self.get_object()
        if error := self._terminal_guard(issue):
            return error
        if not issue.user_is_representative(
            request.user, RemediationIssue.Side.LEAD
        ):
            return self._error(
                "onlyLeadRepresentative", drf_status.HTTP_403_FORBIDDEN
            )
        reason = request.data.get("cancellation_reason")
        if reason not in RemediationIssue.CancellationReason.values:
            return self._error("cancellationReasonRequired")
        issue.status = RemediationIssue.Status.CANCELLED
        issue.cancellation_reason = reason
        issue.save()
        return Response({"status": issue.status})

    @action(detail=True, methods=["post"], name="Reopen a done issue")
    def reopen(self, request, pk=None):
        issue = self.get_object()
        if issue.status != RemediationIssue.Status.DONE:
            return self._error("onlyDoneIssuesCanBeReopened")
        if not issue.user_is_representative(
            request.user, RemediationIssue.Side.LEAD
        ):
            return self._error(
                "onlyLeadRepresentative", drf_status.HTTP_403_FORBIDDEN
            )
        target = request.data.get("status")
        if target not in RemediationIssue.Status.values or target in TERMINAL_STATUSES:
            return self._error("invalidReopenStatus")
        # Previous closure data stays in the audit history (§10.7).
        issue.status = target
        issue.closed_at = None
        issue.resolution = ""
        issue.closure_justification = ""
        issue.save()
        return Response({"status": issue.status})


class CommitmentVersionViewSet(BaseModelViewSet):
    """Read-only: versions are created and accepted through the Issue actions."""

    model = CommitmentVersion
    serializers_module = "issues.serializers"
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["issue", "folder"]
    search_fields = ["text"]
    ordering = ["-version_number"]

from django.db import IntegrityError, transaction
from rest_framework import serializers
from django.conf import settings
from core.models import ComplianceAssessment, Framework, RequirementAssignment

from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.serializers import BaseModelSerializer
from core.utils import RoleCodename, UserGroupCodename
from iam.models import Folder, Role, RoleAssignment, UserGroup
from django.contrib.auth import get_user_model
from tprm.models import (
    Entity,
    EntityAssessment,
    Representative,
    Solution,
    SolutionSubcontractor,
    Contract,
)
from django.utils.translation import gettext_lazy as _

import structlog

logger = structlog.get_logger(__name__)


# Sentinel used to distinguish "client omitted this field" from "client sent an
# empty array" in nested chain writes. Must be a unique object — not None, [],
# or any value a client could legitimately send.
_CHAIN_UNSET = object()

User = get_user_model()


class EntityReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owned_folders = FieldsRelatedField(many=True)
    parent_entity = FieldsRelatedField()
    branches = FieldsRelatedField(many=True)
    relationship = FieldsRelatedField(many=True)
    contracts = FieldsRelatedField(many=True)
    legal_identifiers = serializers.SerializerMethodField()
    default_criticality = serializers.ReadOnlyField()
    filtering_labels = FieldsRelatedField(many=True)
    subcontracts_count = serializers.SerializerMethodField()
    subcontracts_usage = serializers.SerializerMethodField()

    def get_legal_identifiers(self, obj):
        """Format legal identifiers as a readable string for display"""
        if not obj.legal_identifiers:
            return ""
        return "\n".join(
            [f"{key}: {value}" for key, value in obj.legal_identifiers.items()]
        )

    def get_subcontracts_count(self, obj):
        """Number of solutions where this entity is declared as a subcontractor.

        Powers the Entity detail view's "Used as subcontractor in N solutions"
        panel and the disabled-delete-button tooltip. Skipped on the list
        endpoint to avoid one COUNT per row (N+1); computed everywhere else
        (detail, direct serializer use, exports, tests).
        """
        if self.context.get("action") == "list":
            return 0
        return obj.subcontracts.count()

    def get_subcontracts_usage(self, obj):
        """Up to 50 solutions blocking deletion, with parent contract.

        Skipped on the list endpoint to avoid a per-row N+1; computed
        everywhere else.
        """
        if self.context.get("action") == "list":
            return []
        rows = obj.subcontracts.select_related("solution").order_by("solution__name")[
            :50
        ]
        return [
            {
                "id": str(row.id),
                "solution_id": str(row.solution_id),
                "solution_name": row.solution.name,
            }
            for row in rows
        ]

    class Meta:
        model = Entity
        exclude = []


class EntityWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Entity
        exclude = ["owned_folders"]

    def to_internal_value(self, data):
        """Convert None to empty string for CharField DORA fields before validation"""
        dora_char_fields = [
            "country",
            "currency",
            "dora_entity_type",
            "dora_entity_hierarchy",
            "dora_provider_person_type",
        ]
        for field in dora_char_fields:
            if field in data and data[field] is None:
                data[field] = ""
        return super().to_internal_value(data)

    def validate_legal_identifiers(self, value):
        """
        Validate legal identifiers, ensuring LEI is exactly 20 characters if provided.
        """
        if value and isinstance(value, dict):
            lei = value.get("LEI", "")
            # Strip whitespace and check if LEI exists
            if lei:
                lei_stripped = lei.strip()
                if lei_stripped and len(lei_stripped) != 20:
                    raise serializers.ValidationError(_("leiLengthError"))
        return value

    def validate_parent_entity(self, value):
        """
        Validate that an entity cannot be set as its own parent.
        """
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError(
                _("An entity cannot be set as its own parent")
            )
        return value


class EntityImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    owned_folders = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)
    relationship = serializers.SlugRelatedField(
        slug_field="name", read_only=True, many=True
    )

    class Meta:
        model = Entity
        fields = [
            "name",
            "description",
            "folder",
            "mission",
            "reference_link",
            "owned_folders",
            "country",
            "currency",
            "dora_entity_type",
            "dora_entity_hierarchy",
            "dora_assets_value",
            "dora_competent_authority",
            "created_at",
            "updated_at",
            "relationship",
        ]


class EntityAssessmentReadSerializer(BaseModelSerializer):
    compliance_assessment = FieldsRelatedField(fields=["id", "name"])
    evidence = FieldsRelatedField()
    perimeter = FieldsRelatedField()
    entity = FieldsRelatedField()
    folder = FieldsRelatedField()
    solutions = FieldsRelatedField(many=True)
    representatives = FieldsRelatedField(many=True)
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)
    validation_flows = FieldsRelatedField(
        many=True,
        fields=[
            "id",
            "ref_id",
            "status",
            {"approver": ["id", "email", "first_name", "last_name"]},
        ],
        source="validationflow_set",
    )

    class Meta:
        model = EntityAssessment
        exclude = ["penetration", "dependency", "maturity", "trust"]


class EntityAssessmentWriteSerializer(BaseModelSerializer):
    create_audit = serializers.BooleanField(default=False)
    framework = serializers.PrimaryKeyRelatedField(
        queryset=Framework.objects.all(), required=False
    )
    selected_implementation_groups = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    def _extract_audit_data(self, validated_data):
        audit_data = {
            "create_audit": validated_data.pop("create_audit", False),
            "framework": validated_data.pop("framework", None),
            "selected_implementation_groups": validated_data.pop(
                "selected_implementation_groups", None
            ),
        }
        return audit_data

    def _create_or_update_audit(self, instance, audit_data):
        if audit_data["create_audit"]:
            if not audit_data.get("framework"):
                raise serializers.ValidationError(
                    {"framework": [_("Framework required")]}
                )

            with transaction.atomic():
                locked = EntityAssessment.objects.select_for_update().get(
                    pk=instance.pk
                )  # lock entity assessment until the end of the transaction
                if getattr(locked, "compliance_assessment_id", None):
                    raise serializers.ValidationError(
                        {
                            "create_audit": [
                                _("An audit already exists for this assessment")
                            ]
                        }
                    )
                audit = ComplianceAssessment.objects.create(
                    name=locked.name,
                    framework=audit_data["framework"],
                    perimeter=locked.perimeter,
                    selected_implementation_groups=audit_data[
                        "selected_implementation_groups"
                    ],
                )

                enclave = Folder.objects.create(
                    content_type=Folder.ContentType.ENCLAVE,
                    name=f"{instance.entity.name}/{instance.name}",
                    parent_folder=instance.folder,
                )
                audit.folder = enclave
                audit.save()

                audit.create_requirement_assessments()
                audit.reviewers.set(instance.reviewers.all())
                representatives = instance.representatives.all()
                audit.authors.set(
                    [rep.actor for rep in representatives if hasattr(rep, "actor")]
                )
                self._create_requirement_assignment(audit, representatives)
                instance.compliance_assessment = audit
                instance.save()
        else:
            if instance.compliance_assessment:
                audit = instance.compliance_assessment
                audit.reviewers.set(instance.reviewers.all())
                representatives = instance.representatives.all()
                audit.authors.set(
                    [rep.actor for rep in representatives if hasattr(rep, "actor")]
                )
                self._sync_requirement_assignment(audit, representatives)
            instance.save()

    def _sync_requirement_assignment(self, audit, representatives):
        """Create or update the RequirementAssignment so its actors match the representatives."""
        actors = [rep.actor for rep in representatives if hasattr(rep, "actor")]
        assignment = audit.requirement_assignments.first()
        if assignment is None:
            if not actors:
                return
            requirement_assessments = audit.requirement_assessments.all()
            if not requirement_assessments.exists():
                return
            assignment = RequirementAssignment.objects.create(
                compliance_assessment=audit,
                folder=audit.folder,
            )
            assignment.actor.set(actors)
            assignment.requirement_assessments.set(requirement_assessments)
        else:
            assignment.actor.set(actors)

    def _create_requirement_assignment(self, audit, representatives):
        self._sync_requirement_assignment(audit, representatives)

    def _assign_third_party_respondents(
        self,
        instance: EntityAssessment,
        third_party_users: set[User],
        old_third_party_users: set[User] = set(),
    ):
        if instance.compliance_assessment:
            enclave = instance.compliance_assessment.folder
            respondents, _ = UserGroup.objects.get_or_create(
                name=UserGroupCodename.THIRD_PARTY_RESPONDENT,
                folder=enclave,
                builtin=True,
            )
            role_assignment, _ = RoleAssignment.objects.get_or_create(
                user_group=respondents,
                role=Role.objects.get(name=RoleCodename.THIRD_PARTY_RESPONDENT),
                builtin=True,
                folder=enclave,
                is_recursive=True,
            )
            role_assignment.perimeter_folders.add(enclave)
            for user in third_party_users:
                if not user.is_third_party:
                    logger.warning("User is not a third-party", user=user)
                user.user_groups.add(respondents)
            for user in old_third_party_users:
                if not user.is_third_party:
                    logger.warning("User is not a third-party", user=user)
                user.user_groups.remove(respondents)

    def create(self, validated_data):
        audit_data = self._extract_audit_data(validated_data)
        with transaction.atomic():
            instance = super().create(validated_data)
            self._create_or_update_audit(instance, audit_data)
            self._assign_third_party_respondents(
                instance, set(instance.representatives.all())
            )
        return instance

    def update(self, instance: EntityAssessment, validated_data):
        audit_data = self._extract_audit_data(validated_data)
        representatives = set(validated_data.get("representatives", []))
        old_representatives = set(instance.representatives.all()) - set(
            validated_data.get("representatives", [])
        )

        # If perimeter is being changed, update folder to match the new perimeter's folder
        if "perimeter" in validated_data:
            new_perimeter = validated_data["perimeter"]
            if new_perimeter and new_perimeter.folder:
                validated_data["folder"] = new_perimeter.folder

        with transaction.atomic():
            instance = super().update(instance, validated_data)
            self._create_or_update_audit(instance, audit_data)
            if "representatives" in validated_data:
                self._assign_third_party_respondents(
                    instance, representatives, old_representatives
                )
        return instance

    class Meta:
        model = EntityAssessment
        exclude = []


class RepresentativeReadSerializer(BaseModelSerializer):
    entity = FieldsRelatedField()
    user = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)

    class Meta:
        model = Representative
        exclude = []


class RepresentativeWriteSerializer(BaseModelSerializer):
    create_user = serializers.BooleanField(default=False)

    def validate_entity(self, value):
        self._ensure_immutable("entity", value)
        return value

    def _create_or_update_user(self, instance, user):
        if not user:
            return
        user = User.objects.filter(
            email=instance.email,
        ).first()
        if not user:
            send_mail = settings.EMAIL_HOST or settings.EMAIL_HOST_RESCUE
            try:
                user = User.objects.create_user(
                    email=instance.email,
                    first_name=instance.first_name,
                    last_name=instance.last_name,
                    is_third_party=True,
                    keep_local_login=True,
                )
            except Exception as e:
                logger.error(e)
                user = User.objects.filter(email=instance.email).first()
                if user and send_mail:
                    if not user.is_third_party:
                        raise serializers.ValidationError(
                            {"email": "errorUserAlreadyExistsAsInternal"}
                        )
                    user.keep_local_login = True
                    user.save()
                    instance.user = user
                    instance.save()
                    logger.warning("mailing failed")
                    raise serializers.ValidationError(
                        {
                            "warning": [
                                "User created successfully but an error occurred while sending the email"
                            ]
                        }
                    )
                else:
                    raise serializers.ValidationError(
                        {"error": ["An error occurred while creating the user"]}
                    )
        if not user.is_third_party:
            raise serializers.ValidationError(
                {"email": "errorUserAlreadyExistsAsInternal"}
            )
        user.keep_local_login = True
        user.save()
        instance.user = user
        instance.save()

    def create(self, validated_data):
        user = validated_data.pop("create_user", False)
        instance = super().create(validated_data)
        self._create_or_update_user(instance, user)
        return instance

    def update(self, instance, validated_data):
        user = validated_data.pop("create_user", False)
        instance = super().update(instance, validated_data)
        self._create_or_update_user(instance, user)
        return instance

    class Meta:
        model = Representative
        exclude = []


class SolutionSubcontractorReadSerializer(BaseModelSerializer):
    """Nested rows inside SolutionReadSerializer.subcontracting_chain."""

    subcontractor = FieldsRelatedField()
    recipient = FieldsRelatedField()

    class Meta:
        model = SolutionSubcontractor
        fields = ["id", "subcontractor", "recipient"]


class SolutionSubcontractorWriteSerializer(serializers.Serializer):
    """
    Write shape for nested chain rows. Deliberately NOT a ModelSerializer —
    `solution` is set by the parent SolutionWriteSerializer from URL context,
    not accepted from the client. `id` is also ignored; the chain is fully
    replaced on each PATCH.

    `recipient` is optional — null means "direct provider" (the common case
    for fan-out entries directly under the provider).
    """

    subcontractor = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    recipient = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(), required=False, allow_null=True, default=None
    )


class SolutionReadSerializer(BaseModelSerializer):
    provider_entity = FieldsRelatedField()
    recipient_entity = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    contracts = FieldsRelatedField(many=True)
    owner = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(many=True)
    subcontracting_chain = SolutionSubcontractorReadSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = Solution
        exclude = []


class SolutionWriteSerializer(BaseModelSerializer):
    # The chain is handled manually in create()/update() below. Declared here
    # so that `initial_data.get("subcontracting_chain")` is the surface we
    # inspect.
    subcontracting_chain = SolutionSubcontractorWriteSerializer(
        many=True, required=False
    )

    def validate_provider_entity(self, value):
        self._ensure_immutable("provider_entity", value)
        return value

    def validate_subcontracting_chain(self, value):
        """
        Ensure client-side invariants before hitting the DB:
          - No duplicate subcontractor within a single write.
          - Subcontractor != recipient (self-loop).
          - Every recipient must be one of the submitted subcontractors.
          - No cycles in the recipient graph.
          - Subcontractor != direct provider (checked in update/create since
            only then do we have the bound Solution).
        """
        subs = [entry["subcontractor"] for entry in value]
        sub_ids = {s.id for s in subs}
        if len(subs) != len(sub_ids):
            raise serializers.ValidationError(
                _("A subcontractor cannot appear twice in the same chain.")
            )

        # Build directed graph: subcontractor_id → recipient_id
        graph = {}
        for entry in value:
            recipient = entry.get("recipient")
            sub_id = entry["subcontractor"].id
            if recipient:
                if sub_id == recipient.id:
                    raise serializers.ValidationError(
                        _("A subcontractor cannot be its own recipient.")
                    )
                if recipient.id not in sub_ids:
                    raise serializers.ValidationError(
                        _(
                            "Recipient must be one of the submitted "
                            "subcontractors in the chain."
                        )
                    )
                graph[sub_id] = recipient.id

        # Cycle detection via DFS on the recipient graph.
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {sid: WHITE for sid in sub_ids}
        for start in sub_ids:
            if color[start] != WHITE:
                continue
            stack = [start]
            while stack:
                node = stack[-1]
                if color[node] == WHITE:
                    color[node] = GRAY
                    nxt = graph.get(node)
                    if nxt is not None:
                        if color[nxt] == GRAY:
                            raise serializers.ValidationError(
                                _("The subcontracting chain contains a cycle.")
                            )
                        if color[nxt] == WHITE:
                            stack.append(nxt)
                            continue
                color[node] = BLACK
                stack.pop()

        return value

    def _resolve_direct_provider(self, validated_data, instance):
        """Pull the direct provider id from the write data, falling back to instance."""
        provider = validated_data.get("provider_entity")
        if provider is not None:
            return provider.id if hasattr(provider, "id") else provider
        if instance is not None and instance.provider_entity_id is not None:
            return instance.provider_entity_id
        return None

    def _replace_chain(self, solution, chain_data, direct_provider_id):
        """
        Delete all existing SolutionSubcontractor rows for this solution and
        bulk-create the new set inside a single atomic transaction.

        Enforces the self-loop rule here (subcontractor != direct provider)
        because we need the bound solution to resolve it.
        """
        for entry in chain_data:
            if (
                direct_provider_id is not None
                and entry["subcontractor"].id == direct_provider_id
            ):
                raise serializers.ValidationError(
                    {
                        "subcontracting_chain": [
                            _(
                                "A subcontractor cannot be the solution's "
                                "direct provider (rank 1 is implicit)."
                            )
                        ]
                    }
                )

        with transaction.atomic():
            SolutionSubcontractor.objects.filter(solution=solution).delete()
            if chain_data:
                try:
                    SolutionSubcontractor.objects.bulk_create(
                        [
                            SolutionSubcontractor(
                                solution=solution,
                                subcontractor=entry["subcontractor"],
                                recipient=entry.get("recipient"),
                            )
                            for entry in chain_data
                        ]
                    )
                except IntegrityError as exc:
                    raise serializers.ValidationError(
                        {
                            "subcontracting_chain": [
                                _("Chain modified by another user. Refresh and retry.")
                            ],
                        }
                    ) from exc

    def to_internal_value(self, data):
        """Convert None to empty string for CharField DORA fields before validation"""
        dora_char_fields = [
            "dora_ict_service_type",
            "data_location_storage",
            "data_location_processing",
            "dora_data_sensitiveness",
            "dora_reliance_level",
            "dora_substitutability",
            "dora_non_substitutability_reason",
            "dora_has_exit_plan",
            "dora_reintegration_possibility",
            "dora_discontinuing_impact",
            "dora_alternative_providers_identified",
        ]
        for field in dora_char_fields:
            if field in data and data[field] is None:
                data[field] = ""
        return super().to_internal_value(data)

    def create(self, validated_data):
        chain_data = validated_data.pop("subcontracting_chain", _CHAIN_UNSET)
        with transaction.atomic():
            solution = super().create(validated_data)
            if chain_data is not _CHAIN_UNSET:
                self._replace_chain(solution, chain_data, solution.provider_entity_id)
        self._log_chain_event(solution, chain_data, is_create=True)
        return solution

    def update(self, instance, validated_data):
        # Distinguish "omit the field" (leave chain untouched) from "send []"
        # (explicitly clear). `initial_data` preserves the raw presence signal
        # even after validated_data.pop() mutations.
        chain_sent = "subcontracting_chain" in self.initial_data
        chain_data = validated_data.pop("subcontracting_chain", _CHAIN_UNSET)

        with transaction.atomic():
            solution = super().update(instance, validated_data)
            if chain_sent:
                direct_provider_id = self._resolve_direct_provider(
                    validated_data, solution
                )
                self._replace_chain(
                    solution,
                    chain_data if chain_data is not _CHAIN_UNSET else [],
                    direct_provider_id,
                )
        if chain_sent:
            self._log_chain_event(
                solution,
                chain_data if chain_data is not _CHAIN_UNSET else [],
            )
        return solution

    def _log_chain_event(self, solution, chain_data, is_create=False):
        """Emit structured audit log for chain mutations (post-commit)."""
        if chain_data is _CHAIN_UNSET or chain_data is None:
            return
        request = self.context.get("request")
        user_id = getattr(getattr(request, "user", None), "id", None)
        logger.info(
            "solution.subcontracting_chain.updated",
            solution_id=str(solution.id),
            user_id=str(user_id) if user_id else None,
            chain_length=len(chain_data),
            is_create=is_create,
            subcontractor_ids=[str(entry["subcontractor"].id) for entry in chain_data],
        )

    class Meta:
        model = Solution
        exclude = ["recipient_entity"]


class ContractReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    owner = FieldsRelatedField(many=True)
    provider_entity = FieldsRelatedField()
    beneficiary_entity = FieldsRelatedField()
    evidences = FieldsRelatedField(many=True)
    solutions = FieldsRelatedField(many=True)
    overarching_contract = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)
    validation_flows = FieldsRelatedField(
        many=True,
        fields=[
            "id",
            "ref_id",
            "status",
            {"approver": ["id", "email", "first_name", "last_name"]},
        ],
        source="validationflow_set",
    )

    class Meta:
        model = Contract
        exclude = []


class ContractWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Contract
        exclude = []

    def validate_overarching_contract(self, value):
        """
        Validate that a contract cannot be set as its own overarching contract.
        """
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError(
                _("A contract cannot be set as its own overarching contract")
            )
        return value

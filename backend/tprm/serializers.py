import uuid

import structlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    RequirementAssignment,
    Terminology,
)
from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.serializers import BaseModelSerializer
from core.utils import RoleCodename, UserGroupCodename
from iam.models import Folder, Role, RoleAssignment, UserGroup
from pmbok.models import GenericCollection
from tprm.models import (
    Contract,
    Entity,
    EntityAssessment,
    EntityScore,
    Representative,
    Solution,
    SolutionSubcontractor,
)

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
    # The default "Main" entity is created built-in (so it can't be deleted) but
    # is user-owned and fully editable — e.g. renamed to the org's name.
    BUILTIN_EDITABLE_FIELDS = "__all__"

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
    parent_entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    relationship = serializers.SlugRelatedField(
        slug_field="name", read_only=True, many=True
    )

    class Meta:
        model = Entity
        fields = [
            "ref_id",
            "name",
            "description",
            "folder",
            "is_active",
            "mission",
            "reference_link",
            "owned_folders",
            "parent_entity",
            "default_dependency",
            "default_penetration",
            "default_maturity",
            "default_trust",
            "legal_identifiers",
            "country",
            "currency",
            "dora_entity_type",
            "dora_entity_hierarchy",
            "dora_assets_value",
            "dora_competent_authority",
            "dora_provider_person_type",
            "created_at",
            "updated_at",
            "relationship",
        ]


class EntityAssessmentImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    perimeter = HashSlugRelatedField(slug_field="pk", read_only=True)
    entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    compliance_assessment = HashSlugRelatedField(slug_field="pk", read_only=True)
    evidence = HashSlugRelatedField(slug_field="pk", read_only=True)
    solutions = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)

    class Meta:
        model = EntityAssessment
        # authors / reviewers / representatives are User/Actor relations that
        # are not part of a domain export, so they are intentionally omitted.
        fields = [
            "name",
            "description",
            "folder",
            "perimeter",
            "version",
            "status",
            "observation",
            "eta",
            "due_date",
            "criticality",
            "penetration",
            "dependency",
            "maturity",
            "trust",
            "conclusion",
            "reference_link",
            "entity",
            "compliance_assessment",
            "evidence",
            "solutions",
            "created_at",
            "updated_at",
        ]


class RepresentativeImportExportSerializer(BaseModelSerializer):
    entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    email = serializers.EmailField(validators=[], required=False, allow_blank=True)

    class Meta:
        model = Representative
        # user (FK to iam.User) is intentionally omitted: users are not exported.
        fields = [
            "ref_id",
            "entity",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "description",
            "created_at",
            "updated_at",
        ]


class SolutionImportExportSerializer(BaseModelSerializer):
    provider_entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    recipient_entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    assets = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)

    class Meta:
        model = Solution
        # owner (M2M to core.Actor) is intentionally omitted.
        fields = [
            "ref_id",
            "name",
            "description",
            "provider_entity",
            "recipient_entity",
            "is_active",
            "reference_link",
            "criticality",
            "assets",
            "dora_ict_service_type",
            "storage_of_data",
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
            "dora_alternative_providers",
            "created_at",
            "updated_at",
        ]


class SolutionSubcontractorImportExportSerializer(BaseModelSerializer):
    solution = HashSlugRelatedField(slug_field="pk", read_only=True)
    subcontractor = HashSlugRelatedField(slug_field="pk", read_only=True)
    recipient = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = SolutionSubcontractor
        fields = [
            "solution",
            "subcontractor",
            "recipient",
            "created_at",
            "updated_at",
        ]


class ContractImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    provider_entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    beneficiary_entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    overarching_contract = HashSlugRelatedField(slug_field="pk", read_only=True)
    evidences = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)
    solutions = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)

    class Meta:
        model = Contract
        # owner (M2M to core.Actor) is intentionally omitted.
        fields = [
            "ref_id",
            "name",
            "description",
            "folder",
            "provider_entity",
            "beneficiary_entity",
            "overarching_contract",
            "evidences",
            "solutions",
            "status",
            "start_date",
            "end_date",
            "dora_contractual_arrangement",
            "currency",
            "annual_expense",
            "termination_reason",
            "is_intragroup",
            "dora_exclude",
            "governing_law_country",
            "notice_period_entity",
            "notice_period_provider",
            "created_at",
            "updated_at",
        ]


class EntityAssessmentReadSerializer(BaseModelSerializer):
    # Bare, so the value carries `str` and the table can render it as a link to the
    # audit. Only `.id` is read elsewhere.
    compliance_assessment = FieldsRelatedField()
    completion = serializers.SerializerMethodField()
    review_progress = serializers.SerializerMethodField()
    assignment_status = serializers.SerializerMethodField()
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

    def get_completion(self, obj):
        """How far the third party has got with filling the questionnaire in.

        The respondent-facing number, so this column and the respondent's own
        assessment page can never disagree. Distinct from `review_progress`, which
        is the auditor's side and reads 0% however much the third party has answered.
        """
        audit_id = obj.compliance_assessment_id
        if not audit_id:
            return None
        cached = (self.context.get("optimized_data") or {}).get("completion")
        if cached is not None and audit_id in cached:
            return cached[audit_id]
        from core.utils import compute_respondent_progress

        audit = obj.compliance_assessment
        return compute_respondent_progress(
            audit, audit.get_requirement_assessments(include_non_assessable=False)
        )

    def get_review_progress(self, obj):
        """How much of the audit the auditor has assessed."""
        audit_id = obj.compliance_assessment_id
        if not audit_id:
            return None
        cached = (self.context.get("optimized_data") or {}).get("review_progress")
        if cached is not None and audit_id in cached:
            return cached[audit_id]
        return obj.compliance_assessment.progress

    def get_assignment_status(self, obj):
        """Where the questionnaire stands with its respondent.

        An audit can carry several assignments; the least advanced one is what the
        assessment as a whole is still waiting on.
        """
        audit_id = obj.compliance_assessment_id
        if not audit_id:
            return None
        cached = (self.context.get("optimized_data") or {}).get("assignment_statuses")
        if cached is not None:
            statuses = cached.get(audit_id, [])
        else:
            statuses = list(
                obj.compliance_assessment.requirement_assignments.values_list(
                    "status", flat=True
                )
            )
        if not statuses:
            return None
        order = [s.value for s in RequirementAssignment.WORKFLOW_ORDER]
        return min(statuses, key=lambda s: order.index(s) if s in order else len(order))

    class Meta:
        model = EntityAssessment
        exclude = ["penetration", "dependency", "maturity", "trust"]


class EntityAssessmentWriteSerializer(BaseModelSerializer):
    genericcollection = serializers.PrimaryKeyRelatedField(
        source="genericcollection_set",
        many=True,
        required=False,
        queryset=GenericCollection.objects.all(),
    )
    create_audit = serializers.BooleanField(default=False)
    framework = serializers.PrimaryKeyRelatedField(
        queryset=Framework.objects.all(), required=False
    )
    selected_implementation_groups = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    link_audit = serializers.PrimaryKeyRelatedField(
        queryset=ComplianceAssessment.objects.all(), required=False, allow_null=True
    )
    # Set on the audit the assessment creates, so the analyst configures respondent
    # visibility here instead of opening the audit afterwards.
    field_visibility = serializers.JSONField(required=False)

    def _extract_audit_data(self, validated_data):
        audit_data = {
            "create_audit": validated_data.pop("create_audit", False),
            "framework": validated_data.pop("framework", None),
            "selected_implementation_groups": validated_data.pop(
                "selected_implementation_groups", None
            ),
            "link_audit": validated_data.pop("link_audit", None),
            "field_visibility": validated_data.pop("field_visibility", None),
        }
        return audit_data

    def _lock_instance_without_audit(self, instance, field_name):
        locked = EntityAssessment.objects.select_for_update().get(pk=instance.pk)
        if getattr(locked, "compliance_assessment_id", None):
            raise serializers.ValidationError(
                {field_name: [_("An audit already exists for this assessment")]}
            )
        return locked

    def _make_enclave_folder(self, instance):
        return Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=f"{instance.entity.name}/{instance.name}",
            parent_folder=instance.folder,
        )

    def _finalize_linked_audit(self, instance, audit):
        """Shared tail for create/link."""
        audit.reviewers.set(instance.reviewers.all())
        self._default_representatives_from_entity(instance)
        representatives = instance.representatives.all()
        audit.authors.set(
            [rep.actor for rep in representatives if hasattr(rep, "actor")]
        )
        self._create_requirement_assignment(audit, representatives)
        instance.compliance_assessment = audit
        instance.save()

    def _create_audit(self, instance, audit_data):
        if not audit_data.get("framework"):
            raise serializers.ValidationError({"framework": [_("Framework required")]})

        with transaction.atomic():
            locked = self._lock_instance_without_audit(instance, "create_audit")
            from core.utils import EVERYONE_EDIT, build_third_party_field_visibility

            # The editor only sends the pills that were touched, so an explicit map
            # is merged onto the profile rather than replacing it — otherwise moving
            # one pill would drop every other field back to the internal-audit
            # defaults and re-expose the auditor's side to the respondent.
            field_visibility = build_third_party_field_visibility(
                audit_data["framework"]
            )
            for key, pair in (audit_data.get("field_visibility") or {}).items():
                if not isinstance(pair, dict):
                    continue
                field_visibility.setdefault(key, dict(EVERYONE_EDIT))
                field_visibility[key].update(pair)

            # Enclave audits carry no perimeter: the enclave folder, not the
            # entity assessment's perimeter, governs their placement.
            audit = ComplianceAssessment.objects.create(
                name=locked.name,
                framework=audit_data["framework"],
                selected_implementation_groups=audit_data[
                    "selected_implementation_groups"
                ],
                field_visibility=field_visibility,
            )

            enclave = self._make_enclave_folder(instance)
            audit.folder = enclave
            audit.save()

            audit.create_requirement_assessments()
            self._finalize_linked_audit(instance, audit)

    def _link_existing_audit(self, instance, audit_data):
        with transaction.atomic():
            self._lock_instance_without_audit(instance, "link_audit")
            source_audit = ComplianceAssessment.objects.select_for_update().get(
                pk=audit_data["link_audit"].pk
            )
            # Linking relocates the audit itself, so the user needs
            # change_complianceassessment in the audit's current folder —
            # not this serializer's own change_entityassessment.
            self._check_object_perm(source_audit, "change", model=ComplianceAssessment)
            if (
                EntityAssessment.objects.filter(compliance_assessment=source_audit)
                .exclude(pk=instance.pk)
                .exists()
            ):
                # i18n key resolved by the frontend (safeTranslate / messages/*.json)
                raise serializers.ValidationError(
                    {"link_audit": ["auditAlreadyLinkedToEntityAssessment"]}
                )

            enclave = self._make_enclave_folder(instance)

            audit = source_audit
            audit.folder = enclave
            # Enclave audits carry no perimeter — drop the one it had in its
            # previous domain.
            audit.perimeter = None
            audit.save()
            RequirementAssessment.objects.filter(compliance_assessment=audit).update(
                folder=enclave
            )
            Answer.objects.filter(
                requirement_assessment__compliance_assessment=audit
            ).update(folder=enclave)

            self._finalize_linked_audit(instance, audit)

    def _create_or_update_audit(self, instance, audit_data):
        if audit_data["create_audit"]:
            self._create_audit(instance, audit_data)
        elif audit_data.get("link_audit"):
            self._link_existing_audit(instance, audit_data)
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
            # Never revoke someone who is in the final set: an empty submitted list
            # marks every current representative for removal, and the entity defaults
            # can put the same people straight back.
            for user in old_third_party_users - third_party_users:
                if not user.is_third_party:
                    logger.warning("User is not a third-party", user=user)
                user.user_groups.remove(respondents)

    def _default_representatives_from_entity(self, instance):
        """Fall back to the entity's own representatives when none were picked.

        The picker already offers exactly these users; leaving it empty produced an
        assessment nobody could answer — no audit authors, no requirement assignment,
        and nobody in the enclave's respondent group. Runs only where an audit is
        created or linked, so clearing the field on an assessment that already has one
        stays a deliberate clear.
        """
        if instance.representatives.exists():
            return
        users = User.objects.filter(
            representative__entity=instance.entity, is_third_party=True
        ).distinct()
        if users:
            instance.representatives.set(users)

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
            newly_audited = bool(
                audit_data["create_audit"] or audit_data.get("link_audit")
            )
            if newly_audited:
                # Read back from the instance: the submitted list may have been empty
                # and filled from the entity when the audit was built.
                self._assign_third_party_respondents(
                    instance, set(instance.representatives.all()), old_representatives
                )
            elif "representatives" in validated_data:
                self._assign_third_party_respondents(
                    instance, representatives, old_representatives
                )
        return instance

    class Meta:
        model = EntityAssessment
        exclude = []


class EntityScoreReadSerializer(BaseModelSerializer):
    entity = FieldsRelatedField()
    provider = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)
    folder = FieldsRelatedField()
    # 0-100 whatever the provider's scale, so a row is readable next to another's.
    normalized_score = serializers.ReadOnlyField()

    class Meta:
        model = EntityScore
        exclude = []


class EntityScoreWriteSerializer(BaseModelSerializer):
    class Meta:
        model = EntityScore
        exclude = ["folder"]
        # The (entity, provider, as_of) constraint would otherwise become a
        # UniqueTogetherValidator that rejects a replay before `create` can turn it
        # into an update. The constraint still guards writes that skip this
        # serializer, and `create` keeps the API idempotent.
        validators = []

    def to_internal_value(self, data):
        """Accept the provider by name as well as by id.

        Scores arrive from a scheduled feed that knows "Bitsight", not a UUID;
        forcing it to resolve the terminology first is a round-trip for nothing.
        """
        provider = data.get("provider") if hasattr(data, "get") else None
        if isinstance(provider, str) and provider.strip():
            try:
                uuid.UUID(provider)
            except ValueError:
                providers = Terminology.objects.filter(
                    field_path=Terminology.FieldPath.ENTITY_SCORE_PROVIDER,
                    is_visible=True,
                )
                match = providers.filter(name__iexact=provider.strip()).first()
                if match is None:
                    known = ", ".join(sorted(providers.values_list("name", flat=True)))
                    raise serializers.ValidationError(
                        {
                            "provider": [
                                f"Unknown rating provider '{provider}'."
                                + (f" Known providers: {known}." if known else "")
                            ]
                        }
                    )
                data = data.copy()
                data["provider"] = str(match.id)
        return super().to_internal_value(data)

    @staticmethod
    def _existing_reading(validated_data):
        return EntityScore.objects.filter(
            entity=validated_data.get("entity"),
            provider=validated_data.get("provider"),
            as_of=validated_data.get("as_of"),
        ).first()

    def create(self, validated_data):
        """A feed re-run for the same reading corrects it instead of colliding.

        One reading per provider per day, so replaying a day means "already recorded",
        not an error. The retry covers two feeds posting the same reading at once,
        where the row appears between the lookup and the insert.
        """
        existing = self._existing_reading(validated_data)
        if existing is not None:
            return self.update(existing, validated_data)
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            existing = self._existing_reading(validated_data)
            if existing is None:
                raise
            return self.update(existing, validated_data)


class RepresentativeReadSerializer(BaseModelSerializer):
    entity = FieldsRelatedField()
    user = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(many=True)
    # Governing folder, derived the same way as backend enforcement
    # (Folder.get_folder path: entity.folder) so the frontend can scope checks.
    folder = FieldsRelatedField(source="entity.folder")

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
    # Governing folder, derived the same way as backend enforcement
    # (Folder.get_folder path: provider_entity.folder) so the frontend can scope checks.
    folder = FieldsRelatedField(source="provider_entity.folder")
    assets = FieldsRelatedField(many=True)
    contracts = FieldsRelatedField(many=True)
    owner = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(many=True)
    subcontracting_chain = SolutionSubcontractorReadSerializer(
        many=True, read_only=True
    )
    # Raw EBA code (e.g. "eba_TA:S02"), not the display label.
    # So the frontend can map to translation via safeTranslate.
    dora_ict_service_type = serializers.CharField(default="")
    data_location_storage = serializers.CharField(
        source="get_data_location_storage_display", default=""
    )
    data_location_processing = serializers.CharField(
        source="get_data_location_processing_display", default=""
    )
    dora_data_sensitiveness = serializers.CharField(
        source="get_dora_data_sensitiveness_display", default=""
    )
    dora_reliance_level = serializers.CharField(
        source="get_dora_reliance_level_display", default=""
    )
    dora_substitutability = serializers.CharField(
        source="get_dora_substitutability_display", default=""
    )
    dora_non_substitutability_reason = serializers.CharField(
        source="get_dora_non_substitutability_reason_display", default=""
    )
    dora_has_exit_plan = serializers.CharField(
        source="get_dora_has_exit_plan_display", default=""
    )
    dora_reintegration_possibility = serializers.CharField(
        source="get_dora_reintegration_possibility_display", default=""
    )
    dora_discontinuing_impact = serializers.CharField(
        source="get_dora_discontinuing_impact_display", default=""
    )
    dora_alternative_providers_identified = serializers.CharField(
        source="get_dora_alternative_providers_identified_display", default=""
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

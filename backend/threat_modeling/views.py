import uuid
from collections import defaultdict

import structlog
from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import AppliedControl, Asset, Vulnerability
from core.permissions import FeatureFlagRequired
from iam.models import Folder, RoleAssignment
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from sec_intel.models import Technique
from sec_intel.views import build_catalog_matrix
from .models import ThreatModel, ThreatModelNode, ThreatModelEdge

logger = structlog.get_logger(__name__)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "threat_modeling.serializers"


def _validate_related(user, parsed: dict) -> list[str]:
    """Reject linked objects the caller cannot see; save_graph bypasses serializers."""
    errors = []
    root = Folder.get_root_folder()
    for key, model in (
        ("assets", Asset),
        ("applied_controls", AppliedControl),
        ("vulnerabilities", Vulnerability),
    ):
        requested = set()
        for payload in parsed.values():
            for raw in payload.get(key) or []:
                try:
                    requested.add(uuid.UUID(str(raw)))
                except ValueError, AttributeError:
                    errors.append(f"Invalid {key} id '{raw}'.")
        if not requested:
            continue
        try:
            accessible = set(
                RoleAssignment.get_accessible_object_ids(root, user, model)[0]
            )
        except NotImplementedError, Permission.DoesNotExist:
            continue
        for missing in sorted(requested - accessible):
            errors.append(f"{model._meta.model_name} {missing} is not accessible.")
    return errors


def validate_placements(threat_model, placements) -> list[str]:
    """Check (technique, tactic) pairs against the model's catalog."""
    technique_ids = {technique_id for technique_id, _ in placements}
    in_catalog = set(
        Technique.objects.filter(
            id__in=technique_ids, catalog=threat_model.catalog
        ).values_list("id", flat=True)
    )

    allowed = defaultdict(set)
    for technique_id, tactic_id in Technique.tactics.through.objects.filter(
        technique_id__in=in_catalog
    ).values_list("technique_id", "tactic_id"):
        allowed[technique_id].add(tactic_id)

    errors = []
    for technique_id, tactic_id in sorted(placements):
        if technique_id not in in_catalog:
            errors.append(f"Technique {technique_id} is outside the model's catalog.")
        elif tactic_id not in allowed[technique_id]:
            errors.append(
                f"Technique {technique_id} does not belong to tactic {tactic_id}."
            )
    return errors


class ThreatModelViewSet(BaseModelViewSet):
    """
    API endpoint that allows threat models to be viewed or edited.
    """

    feature_flag = "threat_modeling"

    def get_permissions(self):
        return super().get_permissions() + [FeatureFlagRequired()]

    # POST maps to add_* by default, but both mutate an existing model
    permission_overrides = {
        "save_graph": "change_threatmodel",
        "set_techniques": "change_threatmodel",
    }

    model = ThreatModel
    filterset_fields = ["folder", "catalog"]
    search_fields = ["ref_id", "name", "description"]

    @action(detail=True, name="Get the catalog matrix with the selection applied")
    def matrix(self, request, pk):
        threat_model = self.get_object()
        payload = build_catalog_matrix(threat_model.catalog)
        # per cell, not per technique: a tactic changes what the technique means
        payload["selected"] = [
            f"{technique_id}:{tactic_id}"
            for technique_id, tactic_id in threat_model.nodes.filter(
                kind=ThreatModelNode.Kind.TECHNIQUE
            ).values_list("technique_id", "tactic_id")
            if technique_id and tactic_id
        ]
        return Response(payload)

    @action(detail=True, name="Get the graph")
    def graph(self, request, pk):
        threat_model = self.get_object()
        nodes = threat_model.nodes.select_related(
            "technique", "technique__parent", "tactic"
        ).prefetch_related("assets", "applied_controls", "vulnerabilities")
        return Response(
            {
                "tactics": [
                    {
                        "id": tactic.id,
                        "ref_id": tactic.ref_id,
                        "name": tactic.get_name_translated,
                    }
                    for tactic in threat_model.catalog.tactics.order_by(
                        F("order_id").asc(nulls_last=True)
                    )
                ],
                "nodes": [
                    {
                        "id": node.id,
                        "kind": node.kind,
                        "operator": node.operator,
                        "technique": node.technique_id,
                        "ref_id": node.technique.ref_id if node.technique_id else None,
                        "name": (
                            node.technique.get_name_translated
                            if node.technique_id
                            else None
                        ),
                        # a sub-technique name alone is meaningless
                        "parent_name": (
                            node.technique.parent.get_name_translated
                            if node.technique_id and node.technique.parent_id
                            else None
                        ),
                        "tactic": node.tactic_id,
                        "label": node.label,
                        "description": node.description,
                        "is_highlighted": node.is_highlighted,
                        "assets": [asset.id for asset in node.assets.all()],
                        "applied_controls": [
                            control.id for control in node.applied_controls.all()
                        ],
                        "vulnerabilities": [
                            vulnerability.id
                            for vulnerability in node.vulnerabilities.all()
                        ],
                        "properties": node.properties or {},
                        "position_x": node.position_x,
                        "position_y": node.position_y,
                    }
                    for node in nodes
                ],
                "edges": [
                    {"source": edge.source_id, "target": edge.target_id}
                    for edge in threat_model.edges.all()
                ],
                "graph_columns": threat_model.graph_columns or {},
            }
        )

    @action(detail=True, methods=["post"], url_path="save-graph")
    def save_graph(self, request, pk):
        threat_model = self.get_object()
        raw_nodes = request.data.get("nodes")
        raw_edges = request.data.get("edges", [])
        if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
            return Response(
                {"errors": ["nodes and edges must be arrays."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        errors = []
        parsed = {}
        placements = set()

        def as_uuid(value):
            return uuid.UUID(str(value))

        incoming_ids = set()
        for node in raw_nodes:
            if isinstance(node, dict):
                try:
                    incoming_ids.add(as_uuid(node.get("id")))
                except ValueError, AttributeError:
                    continue
        # a client-minted id must not collide with a node owned by another model
        foreign_ids = set(
            ThreatModelNode.objects.filter(id__in=incoming_ids)
            .exclude(threat_model=threat_model)
            .values_list("id", flat=True)
        )

        for index, node in enumerate(raw_nodes):
            if not isinstance(node, dict):
                errors.append(f"Node {index}: invalid payload.")
                continue
            try:
                # the editor mints the row's UUID on drop
                node_id = as_uuid(node.get("id"))
            except ValueError, AttributeError:
                errors.append(f"Node {index}: invalid node id.")
                continue

            kind = node.get("kind") or ThreatModelNode.Kind.TECHNIQUE
            if kind not in ThreatModelNode.Kind.values:
                errors.append(f"Node {index}: unknown kind '{kind}'.")
                continue

            technique_id = tactic_id = None
            operator = None
            if kind == ThreatModelNode.Kind.TECHNIQUE:
                try:
                    technique_id = as_uuid(node.get("technique"))
                    tactic_id = as_uuid(node.get("tactic"))
                except ValueError, AttributeError:
                    errors.append(
                        f"Node {index}: a technique node needs a technique and a tactic."
                    )
                    continue
                placements.add((technique_id, tactic_id))
            elif kind == ThreatModelNode.Kind.OPERATOR:
                operator = node.get("operator")
                if operator not in ThreatModelNode.Operator.values:
                    errors.append(f"Node {index}: operator must be AND or OR.")
                    continue
                # operators sit in their target's lane
                try:
                    tactic_id = (
                        as_uuid(node.get("tactic")) if node.get("tactic") else None
                    )
                except ValueError, AttributeError:
                    errors.append(f"Node {index}: invalid tactic id.")
                    continue

            try:
                position_x = float(node.get("position_x") or 0)
                position_y = float(node.get("position_y") or 0)
            except ValueError, TypeError:
                errors.append(f"Node {index}: position must be a number.")
                continue

            if node_id in foreign_ids:
                errors.append(f"Node {index}: id already used by another threat model.")
                continue

            parsed[node_id] = {
                "kind": kind,
                "technique_id": technique_id,
                "tactic_id": tactic_id,
                "operator": operator,
                "label": str(node.get("label") or "")[:255],
                "description": str(node.get("description") or ""),
                "is_highlighted": bool(node.get("is_highlighted")),
                "properties": node.get("properties") or {},
                "position_x": position_x,
                "position_y": position_y,
                "assets": node.get("assets") or [],
                "applied_controls": node.get("applied_controls") or [],
                "vulnerabilities": node.get("vulnerabilities") or [],
            }

        errors.extend(validate_placements(threat_model, placements))
        errors.extend(_validate_related(request.user, parsed))

        edges = []
        for index, edge in enumerate(raw_edges):
            if not isinstance(edge, dict):
                errors.append(f"Edge {index}: invalid payload.")
                continue
            try:
                source = as_uuid(edge.get("source"))
                target = as_uuid(edge.get("target"))
            except ValueError, AttributeError:
                errors.append(f"Edge {index}: invalid endpoint id.")
                continue
            if source == target:
                errors.append(f"Edge {index}: an edge cannot loop on a single node.")
                continue
            if source not in parsed or target not in parsed:
                errors.append(f"Edge {index}: endpoint is not on the graph.")
                continue
            edges.append((source, target))

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            threat_model.nodes.exclude(id__in=parsed).delete()
            existing = {
                node.id: node for node in threat_model.nodes.select_for_update()
            }

            for node_id, payload in parsed.items():
                assets = payload.pop("assets")
                applied_controls = payload.pop("applied_controls")
                vulnerabilities = payload.pop("vulnerabilities")
                node = existing.get(node_id)
                if node is None:
                    node = ThreatModelNode.objects.create(
                        id=node_id, threat_model=threat_model, **payload
                    )
                else:
                    for field, value in payload.items():
                        setattr(node, field, value)
                    node.save()
                node.assets.set(assets)
                node.applied_controls.set(applied_controls)
                node.vulnerabilities.set(vulnerabilities)
                existing[node_id] = node

            threat_model.edges.all().delete()
            ThreatModelEdge.objects.bulk_create(
                [
                    ThreatModelEdge(
                        threat_model=threat_model,
                        source=existing[source],
                        target=existing[target],
                        folder=threat_model.folder,
                    )
                    for source, target in dict.fromkeys(edges)
                ]
            )

            # lane x is derived; only sizes are persisted
            threat_model.graph_columns = request.data.get("graph_columns") or {}
            threat_model.save()

        return Response({"nodes": len(parsed), "edges": len(set(edges))})

    @action(detail=True, methods=["post"], url_path="set-techniques")
    def set_techniques(self, request, pk):
        threat_model = self.get_object()
        raw = request.data.get("selections")
        if not isinstance(raw, list):
            return Response(
                {"errors": ["selections must be an array."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requested = set()
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                return Response(
                    {"errors": [f"Selection {index}: invalid payload."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                requested.add(
                    (
                        uuid.UUID(str(item.get("technique"))),
                        uuid.UUID(str(item.get("tactic"))),
                    )
                )
            except ValueError, AttributeError:
                return Response(
                    {"errors": [f"Selection {index}: invalid technique or tactic id."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        errors = validate_placements(threat_model, requested)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # the matrix only addresses technique nodes
            technique_nodes = threat_model.nodes.filter(
                kind=ThreatModelNode.Kind.TECHNIQUE
            )
            current = {
                (node.technique_id, node.tactic_id): node for node in technique_nodes
            }
            for key, node in current.items():
                if key not in requested:
                    node.delete()
            ThreatModelNode.objects.bulk_create(
                [
                    ThreatModelNode(
                        threat_model=threat_model,
                        kind=ThreatModelNode.Kind.TECHNIQUE,
                        technique_id=technique_id,
                        tactic_id=tactic_id,
                        folder=threat_model.folder,
                    )
                    for technique_id, tactic_id in requested - set(current)
                ]
            )

        return Response(
            {
                "count": threat_model.nodes.filter(
                    kind=ThreatModelNode.Kind.TECHNIQUE
                ).count()
            }
        )

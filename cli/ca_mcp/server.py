"""Main MCP server entry point for CISO Assistant"""

import logging

from mcp.server.fastmcp import FastMCP

from . import config

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("ciso-assistant")

# Import all tools to register them with the MCP server
from .tools.read_tools import (
    get_risk_scenarios,
    get_risk_scenario,
    get_applied_controls,
    get_audits_progress,
    get_folders,
    get_perimeters,
    get_risk_matrices,
    get_risk_matrix_details,
    get_risk_assessments,
    get_threats,
    get_assets,
    get_incidents,
    get_security_exceptions,
    get_frameworks,
    get_business_impact_analyses,
    get_requirement_assessments,
    get_quantitative_risk_studies,
    get_quantitative_risk_scenarios,
    get_quantitative_risk_hypotheses,
    get_task_templates,
    get_task_template_details,
    get_vulnerabilities,
    get_vulnerability,
    get_asset_classes,
    get_users,
)

from .tools.aggregate_tools import count_objects

from .tools.analysis_tools import (
    get_all_audits_with_metrics,
    get_audit_gap_analysis,
    get_audit_global_score,
)

from .tools.library_tools import (
    get_stored_libraries,
    get_loaded_libraries,
    import_stored_library,
)

from .tools.write_tools import (
    create_folder,
    create_perimeter,
    create_asset,
    create_threat,
    create_applied_control,
    create_risk_assessment,
    create_risk_scenario,
    create_business_impact_analysis,
    create_compliance_assessment,
    create_quantitative_risk_study,
    create_quantitative_risk_scenario,
    create_quantitative_risk_hypothesis,
    refresh_quantitative_risk_study_simulations,
    create_task_template,
    create_vulnerability,
)

from .tools.update_tools import (
    update_asset,
    update_risk_scenario,
    update_applied_control,
    update_requirement_assessment,
    update_requirement_assessments,
    update_quantitative_risk_study,
    update_quantitative_risk_scenario,
    update_quantitative_risk_hypothesis,
    update_task_template,
    delete_task_template,
    update_vulnerability,
    delete_vulnerability,
)

from .tools.tprm_tools import (
    # Read tools
    get_entities,
    get_entity_assessments,
    get_representatives,
    get_solutions,
    get_contracts,
    # Write tools
    create_entity,
    create_entity_assessment,
    create_representative,
    create_solution,
    create_contract,
    # Update tools
    update_entity,
    update_entity_assessment,
    update_representative,
    update_solution,
    update_contract,
)

from .tools.ebios_rm_tools import (
    # Read tools
    get_ebios_rm_studies,
    get_feared_events,
    get_ro_to_couples,
    get_stakeholders,
    get_strategic_scenarios,
    get_attack_paths,
    get_operational_scenarios,
    get_elementary_actions,
    get_operating_modes,
    get_kill_chains,
    # Write tools
    create_ebios_rm_study,
    create_feared_event,
    create_ro_to_couple,
    create_stakeholder,
    create_strategic_scenario,
    create_attack_path,
    create_operational_scenario,
    create_elementary_action,
    create_operating_mode,
    create_kill_chain_step,
    # Update tools
    update_ebios_rm_study,
    update_feared_event,
    update_ro_to_couple,
    update_stakeholder,
    update_strategic_scenario,
    update_attack_path,
    update_operational_scenario,
    update_operating_mode,
    update_kill_chain_step,
)

READ_TOOLS = [
    count_objects,
    get_risk_scenarios,
    get_risk_scenario,
    get_applied_controls,
    get_audits_progress,
    get_folders,
    get_perimeters,
    get_risk_matrices,
    get_risk_matrix_details,
    get_risk_assessments,
    get_threats,
    get_assets,
    get_incidents,
    get_security_exceptions,
    get_frameworks,
    get_business_impact_analyses,
    get_requirement_assessments,
    get_quantitative_risk_studies,
    get_quantitative_risk_scenarios,
    get_quantitative_risk_hypotheses,
    get_task_templates,
    get_task_template_details,
    get_vulnerabilities,
    get_vulnerability,
    get_asset_classes,
    get_users,
    get_all_audits_with_metrics,
    get_audit_gap_analysis,
    get_audit_global_score,
    get_stored_libraries,
    get_loaded_libraries,
    get_entities,
    get_entity_assessments,
    get_representatives,
    get_solutions,
    get_contracts,
    get_ebios_rm_studies,
    get_feared_events,
    get_ro_to_couples,
    get_stakeholders,
    get_strategic_scenarios,
    get_attack_paths,
    get_operational_scenarios,
    get_elementary_actions,
    get_operating_modes,
    get_kill_chains,
]

WRITE_TOOLS = [
    import_stored_library,
    create_folder,
    create_perimeter,
    create_asset,
    create_threat,
    create_applied_control,
    create_risk_assessment,
    create_risk_scenario,
    create_business_impact_analysis,
    create_compliance_assessment,
    create_quantitative_risk_study,
    create_quantitative_risk_scenario,
    create_quantitative_risk_hypothesis,
    refresh_quantitative_risk_study_simulations,
    create_task_template,
    create_vulnerability,
    update_vulnerability,
    delete_vulnerability,
    update_asset,
    update_risk_scenario,
    update_applied_control,
    update_requirement_assessment,
    update_requirement_assessments,
    update_quantitative_risk_study,
    update_quantitative_risk_scenario,
    update_quantitative_risk_hypothesis,
    update_task_template,
    delete_task_template,
    create_entity,
    create_entity_assessment,
    create_representative,
    create_solution,
    create_contract,
    update_entity,
    update_entity_assessment,
    update_representative,
    update_solution,
    update_contract,
    create_ebios_rm_study,
    create_feared_event,
    create_ro_to_couple,
    create_stakeholder,
    create_strategic_scenario,
    create_attack_path,
    create_operational_scenario,
    create_elementary_action,
    create_operating_mode,
    create_kill_chain_step,
    update_ebios_rm_study,
    update_feared_event,
    update_ro_to_couple,
    update_stakeholder,
    update_strategic_scenario,
    update_attack_path,
    update_operational_scenario,
    update_operating_mode,
    update_kill_chain_step,
]


LOOPBACK_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
LOOPBACK_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]

_registered = False


def _annotations(fn, is_read):
    """Behaviour hints so a client can gate destructive calls. Annotations are
    hints, not a security boundary — the read-only profile is the boundary.

    Read/write comes from which list the tool is in, not from its name: a name
    prefix silently mislabels anything that isn't called get_*.
    """
    from mcp.types import ToolAnnotations

    if is_read:
        return ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True
        )
    name = fn.__name__
    if name.startswith("delete_"):
        return ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=True
        )
    if name.startswith("update_"):
        return ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=True
        )
    # create_/import_/refresh_: additive, and not idempotent
    return ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=False
    )


def register_tools(read_only: bool = False):
    """Register tools with the MCP server, optionally omitting writes."""
    global _registered
    if _registered:
        return
    for tool in READ_TOOLS:
        mcp.tool(annotations=_annotations(tool, is_read=True))(tool)
    if not read_only:
        for tool in WRITE_TOOLS:
            mcp.tool(annotations=_annotations(tool, is_read=False))(tool)
    _registered = True


def run_server():
    """Run the MCP server over stdio"""
    register_tools(read_only=False)
    mcp.run(transport="stdio")


def run_http():
    """Run the MCP server over Streamable HTTP"""
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    register_tools(read_only=config.READ_ONLY)

    mcp.settings.stateless_http = config.STATELESS
    mcp.settings.json_response = config.JSON_RESPONSE
    mcp.settings.streamable_http_path = config.HTTP_PATH

    if config.ALLOWED_HOSTS == ["*"]:
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
        logger.warning(
            "CA_MCP_ALLOWED_HOSTS='*': DNS rebinding protection DISABLED. "
            "Acceptable for tunnel testing, never for a real deployment."
        )
    elif config.ALLOWED_HOSTS:
        # Keep loopback allowed so local tooling (Inspector, curl) still reaches
        # the server once a public hostname is configured.
        # https only: trusting http://<public-host> as an Origin would weaken the
        # rebinding check for no benefit. Loopback plaintext is in LOOPBACK_ORIGINS.
        origins = config.ALLOWED_ORIGINS or [
            f"https://{host}" for host in config.ALLOWED_HOSTS
        ]
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=config.ALLOWED_HOSTS + LOOPBACK_HOSTS,
            allowed_origins=origins + LOOPBACK_ORIGINS,
        )
        logger.info("Allowed hosts: %s", config.ALLOWED_HOSTS + LOOPBACK_HOSTS)
    else:
        logger.warning(
            "CA_MCP_ALLOWED_HOSTS unset: only loopback hosts are accepted. "
            "Set it to the public hostname before exposing this server."
        )

    logger.info(
        "MCP Streamable HTTP on %s:%s%s (read_only=%s, stateless=%s, json=%s, tools=%d)",
        config.HTTP_HOST,
        config.HTTP_PORT,
        config.HTTP_PATH,
        config.READ_ONLY,
        config.STATELESS,
        config.JSON_RESPONSE,
        len(READ_TOOLS) if config.READ_ONLY else len(READ_TOOLS) + len(WRITE_TOOLS),
    )
    uvicorn.run(mcp.streamable_http_app(), host=config.HTTP_HOST, port=config.HTTP_PORT)


def main():
    logging.basicConfig(level=logging.INFO)
    if config.TRANSPORT in ("http", "streamable-http"):
        run_http()
    else:
        run_server()


if __name__ == "__main__":
    main()

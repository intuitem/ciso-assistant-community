"""Main MCP server entry point for CISO Assistant"""

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("ciso-assistant")

# Import all tools to register them with the MCP server
from .tools.read_tools import (
    get_risk_scenarios,
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
)

from .tools.analysis_tools import (
    get_all_audits_with_metrics,
    get_audit_gap_analysis,
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
)

from .tools.update_tools import (
    update_asset,
    update_risk_scenario,
    update_applied_control,
    update_requirement_assessment,
    update_quantitative_risk_study,
    update_quantitative_risk_scenario,
    update_quantitative_risk_hypothesis,
    update_task_template,
    delete_task_template,
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
    # Update tools
    update_ebios_rm_study,
    update_feared_event,
    update_ro_to_couple,
    update_stakeholder,
    update_strategic_scenario,
    update_attack_path,
    update_operational_scenario,
    update_operating_mode,
)

# Register all tools with MCP decorators
mcp.tool()(get_risk_scenarios)
mcp.tool()(get_applied_controls)
mcp.tool()(get_audits_progress)
mcp.tool()(get_folders)
mcp.tool()(get_perimeters)
mcp.tool()(get_risk_matrices)
mcp.tool()(get_risk_matrix_details)
mcp.tool()(get_risk_assessments)
mcp.tool()(get_threats)
mcp.tool()(get_assets)
mcp.tool()(get_incidents)
mcp.tool()(get_security_exceptions)
mcp.tool()(get_frameworks)
mcp.tool()(get_business_impact_analyses)
mcp.tool()(get_requirement_assessments)
mcp.tool()(get_quantitative_risk_studies)
mcp.tool()(get_quantitative_risk_scenarios)
mcp.tool()(get_quantitative_risk_hypotheses)
mcp.tool()(get_task_templates)
mcp.tool()(get_task_template_details)

mcp.tool()(get_all_audits_with_metrics)
mcp.tool()(get_audit_gap_analysis)

mcp.tool()(get_stored_libraries)
mcp.tool()(get_loaded_libraries)
mcp.tool()(import_stored_library)

mcp.tool()(create_folder)
mcp.tool()(create_perimeter)
mcp.tool()(create_asset)
mcp.tool()(create_threat)
mcp.tool()(create_applied_control)
mcp.tool()(create_risk_assessment)
mcp.tool()(create_risk_scenario)
mcp.tool()(create_business_impact_analysis)
mcp.tool()(create_compliance_assessment)
mcp.tool()(create_quantitative_risk_study)
mcp.tool()(create_quantitative_risk_scenario)
mcp.tool()(create_quantitative_risk_hypothesis)
mcp.tool()(refresh_quantitative_risk_study_simulations)
mcp.tool()(create_task_template)

mcp.tool()(update_asset)
mcp.tool()(update_risk_scenario)
mcp.tool()(update_applied_control)
mcp.tool()(update_requirement_assessment)
mcp.tool()(update_quantitative_risk_study)
mcp.tool()(update_quantitative_risk_scenario)
mcp.tool()(update_quantitative_risk_hypothesis)
mcp.tool()(update_task_template)
mcp.tool()(delete_task_template)

# TPRM tools
mcp.tool()(get_entities)
mcp.tool()(get_entity_assessments)
mcp.tool()(get_representatives)
mcp.tool()(get_solutions)
mcp.tool()(get_contracts)
mcp.tool()(create_entity)
mcp.tool()(create_entity_assessment)
mcp.tool()(create_representative)
mcp.tool()(create_solution)
mcp.tool()(create_contract)
mcp.tool()(update_entity)
mcp.tool()(update_entity_assessment)
mcp.tool()(update_representative)
mcp.tool()(update_solution)
mcp.tool()(update_contract)

# EBIOS RM tools
mcp.tool()(get_ebios_rm_studies)
mcp.tool()(get_feared_events)
mcp.tool()(get_ro_to_couples)
mcp.tool()(get_stakeholders)
mcp.tool()(get_strategic_scenarios)
mcp.tool()(get_attack_paths)
mcp.tool()(get_operational_scenarios)
mcp.tool()(get_elementary_actions)
mcp.tool()(get_operating_modes)
mcp.tool()(create_ebios_rm_study)
mcp.tool()(create_feared_event)
mcp.tool()(create_ro_to_couple)
mcp.tool()(create_stakeholder)
mcp.tool()(create_strategic_scenario)
mcp.tool()(create_attack_path)
mcp.tool()(create_operational_scenario)
mcp.tool()(create_elementary_action)
mcp.tool()(create_operating_mode)
mcp.tool()(update_ebios_rm_study)
mcp.tool()(update_feared_event)
mcp.tool()(update_ro_to_couple)
mcp.tool()(update_stakeholder)
mcp.tool()(update_strategic_scenario)
mcp.tool()(update_attack_path)
mcp.tool()(update_operational_scenario)
mcp.tool()(update_operating_mode)


def run_server():
    """Run the MCP server"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()

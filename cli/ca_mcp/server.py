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
)

from .tools.update_tools import (
    update_asset,
    update_risk_scenario,
    update_applied_control,
    update_requirement_assessment,
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

mcp.tool()(update_asset)
mcp.tool()(update_risk_scenario)
mcp.tool()(update_applied_control)
mcp.tool()(update_requirement_assessment)


def run_server():
    """Run the MCP server"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()

from typing import Any

# API endpoint to test
COMPLIANCE_ASSESSMENTS_ENDPOINT = "compliance-assessments-list"
ASSETS_ENDPOINT = "assets-list"
EVIDENCES_ENDPOINT = "evidences-list"
FOLDERS_ENDPOINT = "folders-list"
FRAMEWORKS_ENDPOINT = "frameworks-list"
LIBRARIES_ENDPOINT = "libraries-list"
RISK_MATRICES_ENDPOINT = "risk-matrices-list"
PROJECTS_ENDPOINT = "projects-list"
REQUIREMENT_ASSESSMENTS_ENDPOINT = "requirement-assessments-list"
REQUIREMENT_NODES_ENDPOINT = "requirement-nodes-list"
RISK_ACCEPTANCES_ENDPOINT = "risk-acceptances-list"
RISK_ASSESSMENT_ENDPOINT = "risk-assessments-list"
RISK_SCENARIOS_ENDPOINT = "risk-scenarios-list"
SECURITY_FUNCTIONS_ENDPOINT = "security-functions-list"
SECURITY_MEASURES_ENDPOINT = "security-measures-list"
THREATS_ENDPOINT = "threats-list"
USERS_ENDPOINT = "users-list"

# Common URN used primarily inside tests
TEST_FRAMEWORK_URN = "urn:intuitem:risk:library:nist-csf-1.1"
TEST_FRAMEWORK2_URN = "urn:intuitem:risk:library:iso27001-2022"
TEST_DOCUMENTS_URN = "urn:intuitem:risk:library:doc-pol"
TEST_RISK_MATRIX_URN = "urn:intuitem:risk:library:critical_risk_matrix_3x3"
TEST_RISK_MATRIX2_URN = "urn:intuitem:risk:library:critical_risk_matrix_5x5"
TEST_REQUIREMENT_NODE_URN = "urn:intuitem:risk:req_node:nist-csf-1.1:rs.an-1"

__globals__ = globals()


def format_endpoint(verbose_name: str) -> str:
    return f"{verbose_name.replace(' ', '_').upper()}_ENDPOINT"


def format_urn(object_name: str) -> str:
    return f"TEST_{object_name.replace(' ', '_').upper()}_URN"


def get_var(varname: str) -> Any:
    if (value := __globals__.get(varname, ...)) is ...:
        raise AttributeError(
            f"The test_vars module doesn't contain any variable named '{varname}' !"
        )
    return value

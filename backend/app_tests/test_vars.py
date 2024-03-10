from typing import Any
from core.apps import (
    AUDITOR_PERMISSIONS_LIST,
    APPROVER_PERMISSIONS_LIST,
    ANALYST_PERMISSIONS_LIST,
    DOMAIN_MANAGER_PERMISSIONS_LIST,
    ADMINISTRATOR_PERMISSIONS_LIST,
)

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
REFERENCE_CONTROLS_ENDPOINT = "reference-controls-list"
APPLIED_CONTROLS_ENDPOINT = "applied-controls-list"
POLICIES_ENDPOINT = "policies-list"
THREATS_ENDPOINT = "threats-list"
USERS_ENDPOINT = "users-list"

# Common URN used primarily inside tests
TEST_FRAMEWORK_URN = "urn:intuitem:risk:library:nist-csf-1.1"
TEST_FRAMEWORK2_URN = "urn:intuitem:risk:library:iso27001-2022"
TEST_DOCUMENTS_URN = "urn:intuitem:risk:library:doc-pol"
TEST_RISK_MATRIX_URN = "urn:intuitem:risk:library:critical_risk_matrix_3x3"
TEST_RISK_MATRIX2_URN = "urn:intuitem:risk:library:critical_risk_matrix_5x5"
TEST_REQUIREMENT_NODE_URN = "urn:intuitem:risk:req_node:nist-csf-1.1:rs.an-1"

TEST_USER_EMAIL = "user@tests.com"
GROUPS_PERMISSIONS = {
    "BI-UG-ADM": {
        "folder": "Global",
        "name": "Global_administrator",
        "perms": ADMINISTRATOR_PERMISSIONS_LIST,
    },
    "BI-UG-GAD": {
        "folder": "Global",
        "name": "Global_auditor",
        "perms": AUDITOR_PERMISSIONS_LIST,
    },
    "BI-UG-GAP": {
        "folder": "Global",
        "name": "Global_approver",
        "perms": APPROVER_PERMISSIONS_LIST,
    },
    "BI-UG-AUD": {
        "folder": "test",
        "name": "Auditor",
        "perms": AUDITOR_PERMISSIONS_LIST,
    },
    "BI-UG-APP": {
        "folder": "test",
        "name": "Approver",
        "perms": APPROVER_PERMISSIONS_LIST,
    },
    "BI-UG-ANA": {
        "folder": "test",
        "name": "Analyst",
        "perms": ANALYST_PERMISSIONS_LIST,
    },
    "BI-UG-DMA": {
        "folder": "test",
        "name": "Domain_Manager",
        "perms": DOMAIN_MANAGER_PERMISSIONS_LIST,
    },
}

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


def get_singular_name(plural_name: str) -> str:
    exceptions = {
        "Libraries": "Library",
        "Risk matrices": "Risk matrix",
        "Policies": "Policy",
    }
    return exceptions.get(
        plural_name, plural_name[:-1] if plural_name.endswith("s") else plural_name
    )

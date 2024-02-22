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
        "perms": [
            "add_user",
            "view_user",
            "change_user",
            "delete_user",
            "add_usergroup",
            "view_usergroup",
            "change_usergroup",
            "delete_usergroup",
            "add_event",
            "view_event",
            "change_event",
            "delete_event",
            "add_asset",
            "view_asset",
            "change_asset",
            "delete_asset",
            "add_threat",
            "view_threat",
            "change_threat",
            "delete_threat",
            "add_securityfunction",
            "view_securityfunction",
            "change_securityfunction",
            "delete_securityfunction",
            "add_folder",
            "change_folder",
            "view_folder",
            "delete_folder",
            "add_project",
            "change_project",
            "delete_project",
            "view_project",
            "add_riskassessment",
            "view_riskassessment",
            "change_riskassessment",
            "delete_riskassessment",
            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",
            "add_policy",
            "view_policy",
            "change_policy",
            "delete_policy",
            "add_riskscenario",
            "view_riskscenario",
            "change_riskscenario",
            "delete_riskscenario",
            "add_riskacceptance",
            "view_riskacceptance",
            "change_riskacceptance",
            "delete_riskacceptance",
            "approve_riskacceptance",
            "add_riskmatrix",
            "view_riskmatrix",
            "change_riskmatrix",
            "delete_riskmatrix",
            "add_complianceassessment",
            "view_complianceassessment",
            "change_complianceassessment",
            "delete_complianceassessment",
            "view_requirementassessment",
            "change_requirementassessment",
            "add_evidence",
            "view_evidence",
            "change_evidence",
            "delete_evidence",
            "add_framework",
            "view_framework",
            "delete_framework",
            "view_requirementnode",
            "view_requirementlevel",  # Permits to see the object on api by an admin
            "add_library",
            "view_library",
            "delete_library",
            "backup",
            "restore",
        ]
    },
    "BI-UG-GAD": {
        "folder": "Global",
        "name": "Global_auditor",
        "perms": [
            "view_project",
            "view_riskassessment",
            "view_securitymeasure",
            "view_policy",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_complianceassessment",
            "view_requirementassessment",
            "view_evidence",
            "view_framework",
        ]
    },
    "BI-UG-GVA": {
        "folder": "Global",
        "name": "Global_validator",
        "perms": [
            "view_project",
            "view_riskassessment",
            "view_securitymeasure",
            "view_policy",
            "view_riskscenario",
            "view_riskacceptance",
            "approve_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_complianceassessment",
            "view_requirementassessment",
            "view_evidence",
            "view_framework",
        ]
    },
    "BI-UG-AUD": {
        "folder": "test",
        "name": "Auditor",
        "perms": [
            "view_project",
            "view_riskassessment",
            "view_securitymeasure",
            "view_policy",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_complianceassessment",
            "view_requirementassessment",
            "view_evidence",
            "view_framework",
        ]
    },
    "BI-UG-VAL": {
        "folder": "test",
        "name": "Validator",
        "perms": [
            "view_project",
            "view_riskassessment",
            "view_securitymeasure",
            "view_policy",
            "view_riskscenario",
            "view_riskacceptance",
            "approve_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_complianceassessment",
            "view_requirementassessment",
            "view_evidence",
            "view_framework",
        ]
    },
    "BI-UG-ANA": {
        "folder": "test",
        "name": "Analyst",
        "perms": [
            "add_project",
            "view_project",
            "change_project",
            "delete_project",
            "add_riskassessment",
            "view_riskassessment",
            "change_riskassessment",
            "delete_riskassessment",
            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",
            "add_policy",
            "view_policy",
            "change_policy",
            "delete_policy",
            "add_riskscenario",
            "view_riskscenario",
            "change_riskscenario",
            "delete_riskscenario",
            "add_riskacceptance",
            "view_riskacceptance",
            "change_riskacceptance",
            "delete_riskacceptance",
            "add_complianceassessment",
            "view_complianceassessment",
            "change_complianceassessment",
            "delete_complianceassessment",
            "view_requirementassessment",
            "change_requirementassessment",
            "add_evidence",
            "view_evidence",
            "change_evidence",
            "delete_evidence",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_framework",
        ]
    },
    "BI-UG-DMA": {
        "folder": "test",
        "name": "Domain_Manager",
        "perms": [
            "change_usergroup",
            "view_usergroup",
            "add_project",
            "change_project",
            "delete_project",
            "view_project",
            "add_riskassessment",
            "view_riskassessment",
            "change_riskassessment",
            "delete_riskassessment",
            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",
            "add_policy",
            "view_policy",
            "change_policy",
            "delete_policy",
            "add_riskscenario",
            "view_riskscenario",
            "change_riskscenario",
            "delete_riskscenario",
            "add_riskacceptance",
            "view_riskacceptance",
            "change_riskacceptance",
            "delete_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "change_folder",
            "add_riskmatrix",
            "view_riskmatrix",
            "change_riskmatrix",
            "delete_riskmatrix",
            "add_complianceassessment",
            "view_complianceassessment",
            "change_complianceassessment",
            "delete_complianceassessment",
            "view_requirementassessment",
            "change_requirementassessment",
            "add_evidence",
            "view_evidence",
            "change_evidence",
            "delete_evidence",
            "view_framework",
        ]
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
    return exceptions.get(plural_name, plural_name[:-1] if plural_name.endswith("s") else plural_name)

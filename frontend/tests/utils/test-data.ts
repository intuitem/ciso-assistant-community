export default {
    assessmentName: "Test assessment",
    assetName: "Test asset",
    evidenceName: "Test evidence",
    folderName: "Test domain",
    projectName: "Test project",
    riskAcceptanceName: "Test risk acceptance",
    riskAssessmentName: "Test risk assessment",
    riskScenarioName: "Test risk scenario",
    securityFunctionName: "Test security function",
    securityMeasureName: "Test security measure",
    threatName: "Test threat",
    description: "Test description",
    file: new URL('../utils/test_image.jpg', import.meta.url).pathname,
    file2: new URL('../utils/test_file.txt', import.meta.url).pathname,
    user: {
        email: "User@tests.com",
        password: "password",
        firstName: "Test",
        lastName: "User",
    },
    usergroups: {
        analyst: "Analyst",
        auditor: "Auditor",
        domainManager: "Domain manager",
        validator: "Validator",
    },
    framework: {
        name: "NIST CSF",
        urn: "urn:intuitem:risk:library:nist-csf-1.1"
    },
    matrix: {
        name: "Critical risk matrix 5x5",
        displayName: "critical 5x5",
        urn: "urn:intuitem:risk:library:critical_risk_matrix_5x5"
    },
    securityFunction: {
        name: "Physical security policy",
        category: "policy",
        library: { 
            name: "Documents and policies",
            urn: "urn:intuitem:risk:library:doc-pol"
        },
        urn: "urn:intuitem:risk:function:POL.PHYSICAL"
    },
    securityFunction2: {
        name: "Controls accountability matrix",
        category: "process",
        library: { 
            name: "Documents and policies",
            urn: "urn:intuitem:risk:library:doc-pol"
        },
        urn: "urn:intuitem:risk:function:DOC.CONTROLS"
    },
    threat: {
        name: "Exfiltration Over Other Network Medium",
        library: {
            name: "Mitre ATT&CK v14 - Threats and mitigations",
            urn: "urn:intuitem:risk:library:mitre-attack-v14"
        },
        urn: "urn:intuitem:risk:threat:mitre-attack:T1011"
    },
    threat2: {
        name: "Exfiltration Over Physical Medium",
        library: {
            name: "Mitre ATT&CK v14 - Threats and mitigations",
            urn: "urn:intuitem:risk:library:mitre-attack-v14"
        },
        urn: "urn:intuitem:risk:threat:mitre-attack:T1052"
    },
    requirement_assessment: {
        name: "RC.RP - Recovery Planning",
        library: {
            name: "NIST CSF",
            urn: "urn:intuitem:risk:library:nist-csf-1.1"
        },
    },
    requirement_assessment2: {
        name: "ID.GV - Governance",
        library: {
            name: "NIST CSF",
            urn: "urn:intuitem:risk:library:nist-csf-1.1"
        },
    }
} as {[key: string]: any};
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
    framework: {
        name: "NIST CSF",
        urn: "urn:intuitem:risk:library:nist-csf-1_1"
    },
    matrix: {
        name: "Critical risk matrix 5x5",
        displayName: "default_5x5",
        urn: "urn:intuitem:risk:library:5x5_critical_risk_matrix"
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
        name: "Cryptographic policy",
        category: "policy",
        library: { 
            name: "Documents and policies",
            urn: "urn:intuitem:risk:library:doc-pol"
        },
        urn: "urn:intuitem:risk:function:POL.CRYPTO"
    },
    threat: {
        name: "T1011 - Exfiltration Over Other Network Medium",
        library: {
            name: "Mitre ATT&CK v14 - Threats and mitigations",
            urn: "urn:intuitem:risk:library:mitre-attack-v14"
        },
        urn: "urn:intuitem:risk:threat:mitre-attack:T1011"
    },
    threat2: {
        name: "T1052 - Exfiltration Over Physical Medium",
        library: {
            name: "Mitre ATT&CK v14 - Threats and mitigations",
            urn: "urn:intuitem:risk:library:mitre-attack-v14"
        },
        urn: "urn:intuitem:risk:threat:mitre-attack:T1052"
    },
    requirement_assessment: {
        name: "RC.RP. Recovery Planning/RC.RP-1",
        library: {
            name: "NIST CSF",
            urn: "urn:intuitem:risk:library:nist-csf-1_1"
        },
    },
    requirement_assessment2: {
        name: "ID.GV. Governance/ID.GV-4",
        library: {
            name: "NIST CSF",
            urn: "urn:intuitem:risk:library:nist-csf-1_1"
        },
    }
} as {[key: string]: any};
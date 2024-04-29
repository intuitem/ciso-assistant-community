export default {
	assessmentName: 'Test assessment',
	assetName: 'Test asset',
	evidenceName: 'Test evidence',
	folderName: 'Test domain',
	projectName: 'Test project',
	riskAcceptanceName: 'Test risk acceptance',
	riskAssessmentName: 'Test risk assessment',
	riskScenarioName: 'Test risk scenario',
	referenceControlName: 'Test reference control',
	appliedControlName: 'Test applied control',
	threatName: 'Test threat',
	description: 'Test description',
	file: new URL('../utils/test_image.jpg', import.meta.url).pathname,
	file2: new URL('../utils/test_file.txt', import.meta.url).pathname,
	user: {
		email: 'User@tests.com',
		password: 'pass123wordTest',
		firstName: 'Test',
		lastName: 'User'
	},
	usergroups: {
		// this lists needs to be updated when updating permissions in apps.py in order to avoid test failures
		analyst: {
			name: 'Analyst',
			perms: [
				'add_project',
				'view_project',
				'change_project',
				'delete_project',
				'add_riskassessment',
				'view_riskassessment',
				'change_riskassessment',
				'delete_riskassessment',
				'add_appliedcontrol',
				'view_appliedcontrol',
				'change_appliedcontrol',
				'delete_appliedcontrol',
				'add_policy',
				'view_policy',
				'change_policy',
				'delete_policy',
				'add_riskscenario',
				'view_riskscenario',
				'change_riskscenario',
				'delete_riskscenario',
				'add_riskacceptance',
				'view_riskacceptance',
				'change_riskacceptance',
				'delete_riskacceptance',
				'add_complianceassessment',
				'view_complianceassessment',
				'change_complianceassessment',
				'delete_complianceassessment',
				'view_requirementassessment',
				'change_requirementassessment',
				'add_evidence',
				'view_evidence',
				'change_evidence',
				'delete_evidence',
				'add_asset',
				'view_asset',
				'change_asset',
				'delete_asset',
				'add_threat',
				'view_threat',
				'change_threat',
				'delete_threat',
				'view_referencecontrol',
				'view_folder',
				'view_usergroup',
				'view_riskmatrix',
				'view_requirementnode',
				'view_framework',
				'view_loadedlibrary',
				'view_user'
			]
		},
		reader: {
			name: 'Reader',
			perms: [
				'view_project',
				'view_riskassessment',
				'view_appliedcontrol',
				'view_policy',
				'view_riskscenario',
				'view_riskacceptance',
				'view_asset',
				'view_threat',
				'view_referencecontrol',
				'view_folder',
				'view_usergroup',
				'view_riskmatrix',
				'view_complianceassessment',
				'view_requirementassessment',
				'view_requirementnode',
				'view_evidence',
				'view_framework',
				'view_loadedlibrary',
				'view_user'
			]
		},
		domainManager: {
			name: 'Domain manager',
			perms: [
				'change_usergroup',
				'view_usergroup',
				'add_project',
				'change_project',
				'delete_project',
				'view_project',
				'add_riskassessment',
				'view_riskassessment',
				'change_riskassessment',
				'delete_riskassessment',
				'add_appliedcontrol',
				'view_appliedcontrol',
				'change_appliedcontrol',
				'delete_appliedcontrol',
				'add_policy',
				'view_policy',
				'change_policy',
				'delete_policy',
				'add_riskscenario',
				'view_riskscenario',
				'change_riskscenario',
				'delete_riskscenario',
				'add_riskacceptance',
				'view_riskacceptance',
				'change_riskacceptance',
				'delete_riskacceptance',
				'add_asset',
				'view_asset',
				'change_asset',
				'delete_asset',
				'add_threat',
				'view_threat',
				'change_threat',
				'delete_threat',
				'view_referencecontrol',
				'view_folder',
				'change_folder',
				'add_riskmatrix',
				'view_riskmatrix',
				'change_riskmatrix',
				'delete_riskmatrix',
				'add_complianceassessment',
				'view_complianceassessment',
				'change_complianceassessment',
				'delete_complianceassessment',
				'view_requirementassessment',
				'change_requirementassessment',
				'add_evidence',
				'view_evidence',
				'change_evidence',
				'delete_evidence',
				'view_requirementnode',
				'view_framework',
				'view_loadedlibrary',
				'view_user'
			]
		},
		approver: {
			name: 'Approver',
			perms: [
				'view_project',
				'view_riskassessment',
				'view_appliedcontrol',
				'view_policy',
				'view_riskscenario',
				'view_riskacceptance',
				'approve_riskacceptance',
				'view_asset',
				'view_threat',
				'view_referencecontrol',
				'view_folder',
				'view_usergroup',
				'view_riskmatrix',
				'view_complianceassessment',
				'view_requirementassessment',
				'view_requirementnode',
				'view_evidence',
				'view_framework',
				'view_loadedlibrary',
				'view_user'
			]
		}
	},
	framework: {
		name: 'NIST CSF v1.1',
		ref: 'NIST-CSF-1.1',
		urn: 'urn:intuitem:risk:library:nist-csf-1.1'
	},
	matrix: {
		name: 'Critical risk matrix 5x5',
		displayName: 'critical 5x5',
		urn: 'urn:intuitem:risk:library:critical_risk_matrix_5x5'
	},
	referenceControl: {
		name: 'Physical security policy',
		category: 'policy',
		library: {
			name: 'Documents and policies',
			ref: 'doc-pol',
			urn: 'urn:intuitem:risk:library:doc-pol'
		},
		urn: 'urn:intuitem:risk:function:POL.PHYSICAL'
	},
	referenceControl2: {
		name: 'Controls accountability matrix',
		category: 'process',
		library: {
			name: 'Documents and policies',
			ref: 'doc-pol',
			urn: 'urn:intuitem:risk:library:doc-pol'
		},
		urn: 'urn:intuitem:risk:function:DOC.CONTROLS'
	},
	threat: {
		name: 'Exfiltration Over Other Network Medium',
		library: {
			name: 'Mitre ATT&CK v14 - Threats and mitigations',
			ref: 'mitre-attack',
			urn: 'urn:intuitem:risk:library:mitre-attack-v14'
		},
		urn: 'urn:intuitem:risk:threat:mitre-attack:T1011'
	},
	threat2: {
		name: 'Exfiltration Over Physical Medium',
		library: {
			name: 'Mitre ATT&CK v14 - Threats and mitigations',
			ref: 'mitre-attack',
			urn: 'urn:intuitem:risk:library:mitre-attack-v14'
		},
		urn: 'urn:intuitem:risk:threat:mitre-attack:T1052'
	},
	requirement_assessment: {
		name: 'RC.RP - Recovery Planning',
		library: {
			name: 'NIST CSF v1.1',
			ref: 'NIST-CSF-1.1',
			urn: 'urn:intuitem:risk:library:nist-csf-1.1'
		}
	},
	requirement_assessment2: {
		name: 'ID.GV - Governance',
		library: {
			name: 'NIST CSF v1.1',
			ref: 'NIST-CSF-1.1',
			urn: 'urn:intuitem:risk:library:nist-csf-1.1'
		}
	}
} as { [key: string]: any };

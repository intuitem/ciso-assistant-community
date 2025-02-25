import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
import type { ComponentType } from 'svelte';
import type { Option } from 'svelte-multiselect';

interface ListViewFilterConfig {
	component: ComponentType;
	props?: { label: string; optionsEndpoint?: string; multiple?: boolean; options?: Option[] };
	hide?: boolean;
}

interface ListViewFieldsConfig {
	[key: string]: {
		head: string[];
		body: string[];
		meta?: string[];
		breadcrumb_link_disabled?: boolean;
		filters?: {
			[key: string]: ListViewFilterConfig | undefined;
		};
	};
}

const YES_NO_OPTIONS = [
	{ label: 'yes', value: 'true' },
	{ label: 'no', value: 'false' }
];

const PERIMETER_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'perimeters/lc_status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const DOMAIN_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'folders?content_type=DO&content_type=GL',
		label: 'domain',
		multiple: true
	}
};

const LABELS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'filtering-labels',
		label: 'filtering_labels',
		optionsLabelField: 'label',
		multiple: true
	}
};

const PRIORITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'applied-controls/priority',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		label: 'priority',
		multiple: true
	}
};

const EFFORT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'applied-controls/effort',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		label: 'effort',
		multiple: true
	}
};

const PERIMETER_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'perimeter',
		optionsEndpoint: 'perimeters',
		multiple: true
	}
};

const RISK_ASSESSMENT_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'risk-assessments/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const COMPLIANCE_ASSESSMENT_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'compliance-assessments/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const APPLIED_CONTROL_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'applied-controls/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const TREATMENT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'risk-scenarios/treatment',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'treatment',
		browserCache: 'force-cache',
		multiple: true
	}
};

const STATE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'risk-acceptances/state',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'state',
		browserCache: 'force-cache',
		multiple: true
	}
};

const APPROVER_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'approver',
		optionsEndpoint: 'users?is_approver=true',
		optionsLabelField: 'email',
		multiple: true
	}
};

const RISK_ASSESSMENT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'riskAssessment',
		optionsEndpoint: 'risk-assessments',
		multiple: true
	}
};

const PROVIDER_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'provider',
		optionsEndpoint: 'stored-libraries/provider',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		multiple: true
	}
};

const THREAT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'threats',
		label: 'threat',
		multiple: true
	}
};

const ASSET_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'assets',
		label: 'asset',
		multiple: true
	}
};

const QUALIFICATION_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'qualification',
		optionsEndpoint: 'qualifications',
		multiple: true
	}
};

const RISK_IMPACT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'gravity',
		optionsEndpoint: 'risk-matrices/impact',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		multiple: true
	}
};

const RISK_PROBABILITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'likelihood',
		optionsEndpoint: 'risk-matrices/probability',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		multiple: true
	}
};

const IS_SELECTED_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'is_selected',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const RISK_ORIGIN_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'risk_origin',
		optionsEndpoint: 'ro-to/risk-origin',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		multiple: true
	}
};

const FEARED_EVENT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'feared_event',
		optionsEndpoint: 'feared-events',
		multiple: true
	}
};

const PERTINENCE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'pertinence',
		optionsEndpoint: 'ro-to/pertinence',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		multiple: true
	}
};

const ENTITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'entity',
		optionsEndpoint: 'entities',
		multiple: true
	}
};

const RISK_LEVEL_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'current_level',
		optionsEndpoint: 'risk-matrices/risk',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		multiple: true
	}
};

// TODO: TEST THIS
const CURRENT_CRITICALITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'current_criticality',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		options: [1, 2, 3, 4],
		multiple: true
	}
};

// TODO: TEST THIS
const RESIDUAL_CRITICALITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'residual_criticality',
		options: [1, 2, 3, 4],
		optionsLabelField: 'label',
		optionsValueField: 'value',
		multiple: true
	}
};

const STAKEHOLDER_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'stakeholder',
		optionsEndpoint: 'stakeholders',
		optionsLabelField: 'str',
		multiple: true
	}
};

const FRAMEWORK_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'framework',
		optionsEndpoint: 'frameworks',
		multiple: true
	}
};

const LANGUAGE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'language',
		optionsEndpoint: 'stored-libraries/locale',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		multiple: true
	}
};

const ASSET_TYPE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'type',
		optionsEndpoint: 'assets/type',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		multiple: true
	}
};

const REFERENCE_CONTROL_CATEGORY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'category',
		optionsEndpoint: 'reference-controls/category',
		multiple: true,
		optionsLabelField: 'label',
		browserCache: 'force-cache',
		optionsValueField: 'value'
	}
};

const STAKEHOLDER_CATEGORY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'category',
		optionsEndpoint: 'stakeholders/category',
		multiple: true,
		optionsLabelField: 'label',
		browserCache: 'force-cache',
		optionsValueField: 'value'
	}
};

const CSF_FUNCTION_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'reference-controls/csf_function',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'csfFunction',
		browserCache: 'force-cache',
		multiple: true
	}
};

const OWNER_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'owner',
		optionsLabelField: 'email',
		optionsValueField: 'id',
		optionsEndpoint: 'applied-controls/owner',
		multiple: true
	}
};

const HAS_UPDATE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'updateAvailable',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const LIBRARY_TYPE_FILTER = {
	component: AutocompleteSelect,
	props: {
		label: 'objectType',
		optionsEndpoint: 'stored-libraries/object_type',
		optionsLabelField: 'label',
		optionsValueField: 'label',
		browserCache: 'force-cache',
		multiple: true
	}
};

export const listViewFields = {
	folders: {
		head: ['name', 'description', 'parentDomain'],
		body: ['name', 'description', 'parent_folder']
	},
	perimeters: {
		head: ['ref_id', 'name', 'description', 'domain'],
		body: ['ref_id', 'name', 'description', 'folder'],
		filters: {
			folder: DOMAIN_FILTER,
			lc_status: PERIMETER_STATUS_FILTER
		}
	},
	'filtering-labels': {
		head: ['label'],
		body: ['label']
	},
	'risk-matrices': {
		head: ['name', 'description', 'provider', 'domain'],
		body: ['name', 'description', 'provider', 'folder'],
		meta: ['id', 'urn'],
		filters: {
			folder: DOMAIN_FILTER
		}
	},
	vulnerabilities: {
		head: [
			'ref_id',
			'name',
			'description',
			'status',
			'severity',
			'applied_controls',
			'folder',
			'labels'
		],
		body: [
			'ref_id',
			'name',
			'description',
			'status',
			'severity',
			'applied_controls',
			'folder',
			'filtering_labels'
		],
		filters: {
			folder: DOMAIN_FILTER,
			filtering_labels: LABELS_FILTER
		}
	},
	'risk-assessments': {
		head: ['ref_id', 'name', 'riskMatrix', 'description', 'riskScenarios', 'perimeter'],
		body: ['ref_id', 'str', 'risk_matrix', 'description', 'risk_scenarios_count', 'perimeter'],
		filters: {
			folder: DOMAIN_FILTER,
			perimeter: PERIMETER_FILTER,
			status: RISK_ASSESSMENT_STATUS_FILTER
		}
	},
	threats: {
		head: ['ref_id', 'name', 'description', 'provider', 'domain'],
		body: ['ref_id', 'name', 'description', 'provider', 'folder'],
		meta: ['id', 'urn'],
		filters: {
			folder: DOMAIN_FILTER,
			provider: PROVIDER_FILTER
		}
	},
	'risk-scenarios': {
		head: [
			'ref_id',
			'threats',
			'name',
			'existingAppliedControls',
			'currentLevel',
			'extraAppliedControls',
			'residualLevel',
			'treatment',
			'riskAssessment'
		],
		body: [
			'ref_id',
			'threats',
			'name',
			'existing_applied_controls',
			'current_level',
			'applied_controls',
			'residual_level',
			'treatment',
			'risk_assessment'
		],
		filters: {
			folder: DOMAIN_FILTER,
			perimeter: PERIMETER_FILTER,
			treatment: TREATMENT_FILTER,
			risk_assessment: RISK_ASSESSMENT_FILTER,
			threats: THREAT_FILTER,
			assets: ASSET_FILTER,
			current_level: RISK_LEVEL_FILTER,
			residual_level: RISK_LEVEL_FILTER
		}
	},
	'risk-acceptances': {
		head: ['name', 'description', 'riskScenarios'],
		body: ['name', 'description', 'risk_scenarios'],
		filters: {
			folder: DOMAIN_FILTER,
			state: STATE_FILTER,
			approver: APPROVER_FILTER
		}
	},
	'applied-controls': {
		head: [
			'ref_id',
			'name',
			'priority',
			'status',
			'category',
			'csfFunction',
			'eta',
			'owner',
			'domain',
			'referenceControl'
		],
		body: [
			'ref_id',
			'name',
			'priority',
			'status',
			'category',
			'csf_function',
			'eta',
			'owner',
			'folder',
			'reference_control'
		],
		filters: {
			folder: DOMAIN_FILTER,
			status: APPLIED_CONTROL_STATUS_FILTER,
			category: REFERENCE_CONTROL_CATEGORY_FILTER,
			csf_function: CSF_FUNCTION_FILTER,
			owner: OWNER_FILTER,
			priority: PRIORITY_FILTER,
			effort: EFFORT_FILTER
		}
	},
	policies: {
		head: [
			'ref_id',
			'name',
			'priority',
			'status',
			'csfFunction',
			'eta',
			'owner',
			'domain',
			'referenceControl'
		],
		body: [
			'ref_id',
			'name',
			'priority',
			'status',
			'csf_function',
			'eta',
			'owner',
			'folder',
			'reference_control'
		],
		filters: {
			folder: DOMAIN_FILTER,
			status: APPLIED_CONTROL_STATUS_FILTER,
			csf_function: CSF_FUNCTION_FILTER,
			owner: OWNER_FILTER,
			priority: PRIORITY_FILTER
		}
	},
	'reference-controls': {
		head: ['ref_id', 'name', 'description', 'category', 'csfFunction', 'provider', 'domain'],
		body: ['ref_id', 'name', 'description', 'category', 'csf_function', 'provider', 'folder'],
		meta: ['id', 'urn'],
		filters: {
			folder: DOMAIN_FILTER,
			category: REFERENCE_CONTROL_CATEGORY_FILTER,
			provider: PROVIDER_FILTER,
			csf_function: CSF_FUNCTION_FILTER
		}
	},
	assets: {
		head: [
			'ref_id',
			'name',
			'type',
			'description',
			'securityObjectives',
			'disasterRecoveryObjectives',
			'owner',
			'domain',
			'labels'
		],
		body: [
			'ref_id',
			'name',
			'type',
			'description',
			'security_objectives',
			'disaster_recovery_objectives',
			'owner',
			'folder',
			'filtering_labels'
		],
		filters: {
			folder: DOMAIN_FILTER,
			type: ASSET_TYPE_FILTER,
			filtering_labels: LABELS_FILTER
		}
	},
	users: {
		head: ['email', 'firstName', 'lastName', 'is_sso', 'is_third_party'],
		body: ['email', 'first_name', 'last_name', 'is_sso', 'is_third_party']
	},
	'user-groups': {
		head: ['name'],
		body: ['localization_dict'],
		meta: ['id', 'builtin']
	},
	roles: {
		head: ['name', 'description'],
		body: ['name', 'description']
	},
	'role-assignments': {
		head: ['user', 'userGroup', 'role', 'perimeter'],
		body: ['user', 'user_group', 'role', 'perimeter_folders']
	},
	frameworks: {
		head: ['name', 'description', 'provider', 'complianceAssessments', 'domain'],
		body: ['name', 'description', 'provider', 'compliance_assessments', 'folder'],
		meta: ['id', 'urn'],
		filters: {
			folder: DOMAIN_FILTER,
			provider: PROVIDER_FILTER
		}
	},
	'compliance-assessments': {
		head: ['ref_id', 'name', 'framework', 'description', 'perimeter', 'reviewProgress'],
		body: ['ref_id', 'name', 'framework', 'description', 'perimeter', 'progress'],
		filters: {
			folder: DOMAIN_FILTER,
			perimeter: PERIMETER_FILTER,
			framework: FRAMEWORK_FILTER,
			status: COMPLIANCE_ASSESSMENT_STATUS_FILTER
		}
	},
	'requirement-assessments': {
		head: ['name', 'description', 'complianceAssessment'],
		body: ['name', 'description', 'compliance_assessment'],
		breadcrumb_link_disabled: true
	},
	evidences: {
		head: ['name', 'file', 'size', 'description', 'folder'],
		body: ['name', 'attachment', 'size', 'description', 'folder'],
		filters: {
			folder: DOMAIN_FILTER
		}
	},
	requirements: {
		head: ['ref_id', 'name', 'description', 'framework'],
		body: ['ref_id', 'name', 'description', 'framework'],
		meta: ['id', 'urn']
	},
	libraries: {
		head: ['provider', 'name', 'description', 'language', 'overview'],
		body: ['provider', 'name', 'description', 'locales', 'overview']
	},
	'stored-libraries': {
		head: ['provider', 'ref_id', 'name', 'description', 'language', 'overview', 'publication_date'],
		body: ['provider', 'ref_id', 'name', 'description', 'locales', 'overview', 'publication_date'],
		filters: {
			locale: LANGUAGE_FILTER,
			provider: PROVIDER_FILTER,
			object_type: LIBRARY_TYPE_FILTER
		}
	},
	'loaded-libraries': {
		head: ['provider', 'ref_id', 'name', 'description', 'language', 'overview', 'publication_date'],
		body: ['provider', 'ref_id', 'name', 'description', 'locales', 'overview', 'publication_date'],
		filters: {
			locale: LANGUAGE_FILTER,
			provider: PROVIDER_FILTER,
			object_type: LIBRARY_TYPE_FILTER,
			has_update: HAS_UPDATE_FILTER
		}
	},
	'sso-settings': {
		head: ['name', 'provider', 'providerId'],
		body: ['name', 'provider', 'provider_id']
	},
	'requirement-mapping-sets': {
		head: ['sourceFramework', 'targetFramework'],
		body: ['source_framework', 'target_framework']
	},
	entities: {
		head: ['name', 'description', 'domain', 'ownedFolders'],
		body: ['name', 'description', 'folder', 'owned_folders'],
		filters: {
			folder: DOMAIN_FILTER
		}
	},
	'entity-assessments': {
		head: ['name', 'description', 'perimeter', 'entity'],
		body: ['name', 'description', 'perimeter', 'entity'],
		filters: {
			perimeter: PERIMETER_FILTER,
			status: COMPLIANCE_ASSESSMENT_STATUS_FILTER
		}
	},
	solutions: {
		head: ['name', 'description', 'providerEntity', 'recipientEntity', 'criticality'],
		body: ['name', 'description', 'provider_entity', 'recipient_entity', 'criticality']
	},
	representatives: {
		head: ['email', 'entity', 'role'],
		body: ['email', 'entity', 'role']
	},
	'ebios-rm': {
		head: ['name', 'description'],
		body: ['name', 'description']
	},
	'feared-events': {
		head: ['selected', 'name', 'assets', 'description', 'qualifications', 'gravity'],
		body: ['is_selected', 'name', 'assets', 'description', 'qualifications', 'gravity'],
		filters: {
			assets: ASSET_FILTER,
			qualifications: QUALIFICATION_FILTER,
			gravity: RISK_IMPACT_FILTER,
			is_selected: IS_SELECTED_FILTER
		}
	},
	'ro-to': {
		head: ['isSelected', 'riskOrigin', 'targetObjective', 'fearedEvents', 'pertinence'],
		body: ['is_selected', 'risk_origin', 'target_objective', 'feared_events', 'pertinence'],
		filters: {
			is_selected: IS_SELECTED_FILTER,
			risk_origin: RISK_ORIGIN_FILTER,
			feared_events: FEARED_EVENT_FILTER,
			pertinence: PERTINENCE_FILTER
		}
	},
	stakeholders: {
		head: [
			'is_selected',
			'entity',
			'category',
			'current_criticality',
			'applied_controls',
			'residual_criticality'
		],
		body: [
			'is_selected',
			'entity',
			'category',
			'current_criticality',
			'applied_controls',
			'residual_criticality'
		],
		filters: {
			is_selected: IS_SELECTED_FILTER,
			entity: ENTITY_FILTER,
			category: STAKEHOLDER_CATEGORY_FILTER,
			current_criticality: CURRENT_CRITICALITY_FILTER,
			residual_criticality: RESIDUAL_CRITICALITY_FILTER
		}
	},
	'strategic-scenarios': {
		head: ['ref_id', 'name', 'description', 'ro_to_couple', 'attackPaths', 'gravity'],
		body: ['ref_id', 'name', 'description', 'ro_to_couple', 'attack_paths', 'gravity'],
		filters: {
			gravity: RISK_IMPACT_FILTER
		}
	},
	'attack-paths': {
		head: [
			'is_selected',
			'ref_id',
			'name',
			'risk_origin',
			'target_objective',
			'stakeholders',
			'attackPath'
		],
		body: [
			'is_selected',
			'ref_id',
			'name',
			'risk_origin',
			'target_objective',
			'stakeholders',
			'description'
		],
		filters: {
			is_selected: IS_SELECTED_FILTER,
			stakeholders: STAKEHOLDER_FILTER
		}
	},
	'operational-scenarios': {
		head: ['is_selected', 'operatingModesDescription', 'threats', 'likelihood'],
		body: ['is_selected', 'operating_modes_description', 'threats', 'likelihood'],
		filters: {
			threats: THREAT_FILTER,
			likelihood: RISK_PROBABILITY_FILTER,
			is_selected: IS_SELECTED_FILTER
		}
	},
	'security-exceptions': {
		head: ['ref_id', 'name', 'severity', 'status', 'expiration_date', 'domain'],
		body: ['ref_id', 'name', 'severity', 'status', 'expiration_date', 'folder']
	},
	'findings-assessments': {
		head: ['ref_id', 'name', 'description', 'category', 'findings', 'perimeter'],
		body: ['ref_id', 'str', 'description', 'category', 'findings_count', 'perimeter']
	},
	findings: {
		head: ['ref_id', 'name', 'description', 'findings_assessment', 'status', 'labels'],
		body: ['ref_id', 'str', 'description', 'findings_assessment', 'status', 'filtering_labels']
	},
	extra: {
		filters: {
			risk: undefined,
			probability: undefined,
			impact: undefined,
			likelihood: undefined,
			gravity: undefined
		}
	}
} as const satisfies ListViewFieldsConfig;

export type FilterKeys = {
	[K in keyof typeof listViewFields]: (typeof listViewFields)[K] extends { filters: infer F }
		? keyof F
		: never;
}[keyof typeof listViewFields];

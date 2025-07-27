import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
import type { ComponentType } from 'svelte';
import type { Option } from 'svelte-multiselect';

import ChangeStatus from '$lib/components/ContextMenu/applied-controls/ChangeStatus.svelte';
import { getModelInfo } from './crud';
import SelectObject from '$lib/components/ContextMenu/ebios-rm/SelectObject.svelte';

export function tableSourceMapper(source: any[], keys: string[]): any[] {
	return source.map((row) => {
		const mappedRow: any = {};
		keys.forEach((key) => (mappedRow[key] = row[key]));
		return mappedRow;
	});
}

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

const TASK_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'task-nodes/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const INCIDENT_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'incidents/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const INCIDENT_DETECTION_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'incidents/detection',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'detection',
		browserCache: 'force-cache',
		multiple: true
	}
};
const INCIDENT_SEVERITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'incidents/severity',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'severity',
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

const PROCESSING_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'processings',
		label: 'processing',
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

const PERSONAL_DATA_CATEGORY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'personal-data/category',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'category',
		browserCache: 'force-cache',
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

const CURRENT_RISK_LEVEL_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'current_level',
		optionsEndpoint: 'risk-matrices/risk',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		multiple: true
	}
};

const RESIDUAL_RISK_LEVEL_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		...CURRENT_RISK_LEVEL_FILTER.props,
		label: 'residual_level'
	}
};

const INHERENT_RISK_LEVEL_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		...CURRENT_RISK_LEVEL_FILTER.props,
		label: 'inherent_level'
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
		...CURRENT_CRITICALITY_FILTER.props,
		label: 'residual_criticality'
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

const ASSET_CLASS_FILTER: ListViewFilterConfig = {
	//still broken
	component: AutocompleteSelect,
	props: {
		label: 'assetClass',
		optionsEndpoint: 'asset-class',
		optionsLabelField: 'full_path',
		optionsValueField: 'id',
		multiple: false
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

const MAPPING_SUGGESTED_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'mappingSuggested',
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
		head: ['ref_id', 'name', 'description', 'defaultAssignee', 'domain'],
		body: ['ref_id', 'name', 'description', 'default_assignee', 'folder'],
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
			folder: DOMAIN_FILTER,
			provider: {
				...PROVIDER_FILTER,
				props: { ...PROVIDER_FILTER.props, optionsEndpoint: 'risk-matrices/provider' }
			}
		}
	},
	vulnerabilities: {
		head: ['ref_id', 'name', 'status', 'severity', 'applied_controls', 'folder', 'labels'],
		body: [
			'ref_id',
			'name',
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
		head: ['ref_id', 'name', 'description', 'provider', 'domain', 'labels'],
		body: ['ref_id', 'name', 'description', 'provider', 'folder', 'filtering_labels'],
		meta: ['id', 'urn'],
		filters: {
			folder: DOMAIN_FILTER,
			provider: {
				...PROVIDER_FILTER,
				props: { ...PROVIDER_FILTER.props, optionsEndpoint: 'threats/provider' }
			},
			filtering_labels: LABELS_FILTER
		}
	},
	'risk-scenarios': {
		head: [
			'ref_id',
			'threats',
			'name',
			'inherentLevel',
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
			'inherent_level',
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
			current_level: CURRENT_RISK_LEVEL_FILTER,
			residual_level: RESIDUAL_RISK_LEVEL_FILTER
		}
	},
	'risk-acceptances': {
		head: ['name', 'description', 'riskScenarios', 'state'],
		body: ['name', 'description', 'risk_scenarios', 'state'],
		filters: {
			folder: DOMAIN_FILTER,
			state: STATE_FILTER,
			approver: APPROVER_FILTER
		}
	},
	'applied-controls': {
		head: ['ref_id', 'name', 'priority', 'status', 'category', 'eta', 'domain', 'labels'],
		body: ['ref_id', 'name', 'priority', 'status', 'category', 'eta', 'folder', 'filtering_labels'],
		filters: {
			folder: DOMAIN_FILTER,
			status: APPLIED_CONTROL_STATUS_FILTER,
			category: REFERENCE_CONTROL_CATEGORY_FILTER,
			csf_function: CSF_FUNCTION_FILTER,
			owner: OWNER_FILTER,
			priority: PRIORITY_FILTER,
			effort: EFFORT_FILTER,
			filtering_labels: LABELS_FILTER,
			eta__lte: undefined
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
		head: [
			'ref_id',
			'name',
			'description',
			'category',
			'csfFunction',
			'provider',
			'domain',
			'labels'
		],
		body: [
			'ref_id',
			'name',
			'description',
			'category',
			'csf_function',
			'provider',
			'folder',
			'filtering_labels'
		],
		meta: ['id', 'urn'],
		filters: {
			folder: DOMAIN_FILTER,
			category: REFERENCE_CONTROL_CATEGORY_FILTER,
			provider: {
				...PROVIDER_FILTER,
				props: { ...PROVIDER_FILTER.props, optionsEndpoint: 'reference-controls/provider' }
			},
			csf_function: CSF_FUNCTION_FILTER,
			filtering_labels: LABELS_FILTER
		}
	},
	assets: {
		head: [
			'ref_id',
			'name',
			'type',
			'securityObjectives',
			'disasterRecoveryObjectives',
			'domain',
			'labels'
		],
		body: [
			'ref_id',
			'name',
			'type',
			'security_objectives',
			'disaster_recovery_objectives',
			'folder',
			'filtering_labels'
		],
		filters: {
			folder: DOMAIN_FILTER,
			type: ASSET_TYPE_FILTER,
			filtering_labels: LABELS_FILTER
		}
	},
	'asset-class': {
		head: ['name', 'description'],
		body: ['name', 'description']
	},
	users: {
		head: ['email', 'firstName', 'lastName', 'userGroups', 'keep_local_login', 'is_third_party'],
		body: ['email', 'first_name', 'last_name', 'user_groups', 'keep_local_login', 'is_third_party']
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
			provider: {
				...PROVIDER_FILTER,
				props: { ...PROVIDER_FILTER.props, optionsEndpoint: 'frameworks/provider' }
			}
		}
	},
	'compliance-assessments': {
		head: ['ref_id', 'name', 'framework', 'perimeter', 'reviewProgress', 'createdAt', 'updatedAt'],
		body: ['ref_id', 'name', 'framework', 'perimeter', 'progress', 'created_at', 'updated_at'],
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
		head: ['name', 'file', 'size', 'description', 'folder', 'labels'],
		body: ['name', 'attachment', 'size', 'description', 'folder', 'filtering_labels'],
		filters: {
			folder: DOMAIN_FILTER,
			filtering_labels: LABELS_FILTER
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
			object_type: LIBRARY_TYPE_FILTER,
			mapping_suggested: MAPPING_SUGGESTED_FILTER
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
		body: ['source_framework', 'target_framework'],
		filters: {
			library__provider: {
				...PROVIDER_FILTER,
				props: { ...PROVIDER_FILTER.props, optionsEndpoint: 'requirement-mapping-sets/provider' }
			}
		}
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
	'business-impact-analysis': {
		head: ['name', 'perimeter', 'status'],
		body: ['name', 'perimeter', 'status']
	},
	'asset-assessments': {
		head: [
			'asset',
			'folder',
			'bia',
			'dependencies',
			'associatedControls',
			'recoveryDocumented',
			'recoveryTested',
			'recoveryTargetsMet'
		],
		body: [
			'asset',
			'asset_folder',
			'bia',
			'dependencies',
			'associated_controls',
			'recovery_documented',
			'recovery_tested',
			'recovery_targets_met'
		]
	},
	'escalation-thresholds': {
		head: ['pointInTime', 'assetAssessment', 'qualiImpact', 'impactOn', 'justification'],
		body: ['get_human_pit', 'asset_assessment', 'quali_impact', 'qualifications', 'justification']
	},
	processings: {
		head: ['name', 'description', 'status', 'legalBasis', 'processingNature', 'folder'],
		body: ['name', 'description', 'status', 'legal_basis', 'nature', 'folder']
	},
	purposes: {
		head: ['name', 'description', 'processing'],
		body: ['name', 'description', 'processing'],
		filters: {
			processing: PROCESSING_FILTER
		}
	},
	'personal-data': {
		head: [
			'processing',
			'name',
			'description',
			'category',
			'isSensitive',
			'retention',
			'deletionPolicy'
		],
		body: [
			'processing',
			'name',
			'description',
			'category',
			'is_sensitive',
			'retention',
			'deletion_policy'
		],
		filters: {
			processing: PROCESSING_FILTER,
			category: PERSONAL_DATA_CATEGORY_FILTER
		}
	},
	'data-subjects': {
		head: ['name', 'description', 'category'],
		body: ['name', 'description', 'category']
	},
	'data-recipients': {
		head: ['name', 'description', 'category'],
		body: ['name', 'description', 'category']
	},
	'data-contractors': {
		head: ['name', 'description', 'entity', 'relationshipType', 'country', 'documentationLink'],
		body: ['name', 'description', 'entity', 'relationship_type', 'country', 'documentation_link']
	},
	'data-transfers': {
		head: ['name', 'description', 'entity', 'country', 'legalBasis', 'documentationLink'],
		body: ['name', 'description', 'entity', 'country', 'legal_basis', 'documentation_link']
	},
	'ebios-rm': {
		head: ['name', 'description', 'domain'],
		body: ['name', 'description', 'folder']
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
			'description'
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
		head: ['is_selected', 'attackPath', 'operatingModesDescription', 'threats', 'likelihood'],
		body: ['is_selected', 'attack_path', 'operating_modes_description', 'threats', 'likelihood'],
		filters: {
			threats: THREAT_FILTER,
			likelihood: RISK_PROBABILITY_FILTER,
			is_selected: IS_SELECTED_FILTER
		}
	},
	'elementary-actions': {
		head: ['ref_id', 'domain', '', 'name', 'attack_stage', 'threat'],
		body: ['ref_id', 'domain', 'icon_fa_class', 'name', 'attack_stage', 'threat']
	},
	'operating-modes': {
		head: ['ref_id', 'name', 'likelihood'],
		body: ['ref_id', 'name', 'likelihood']
	},
	'kill-chains': {
		head: ['elementary_action', 'attack_stage', 'antecedents', 'logic_operator'],
		body: ['elementary_action', 'attack_stage', 'antecedents', 'logic_operator']
	},
	'security-exceptions': {
		head: ['ref_id', 'name', 'severity', 'status', 'expiration_date', 'domain'],
		body: ['ref_id', 'name', 'severity', 'status', 'expiration_date', 'folder']
	},
	'findings-assessments': {
		head: ['ref_id', 'name', 'description', 'category', 'evidences', 'findings', 'perimeter'],
		body: ['ref_id', 'name', 'description', 'category', 'evidences', 'findings_count', 'perimeter']
	},
	findings: {
		head: [
			'ref_id',
			'name',
			'findings_assessment',
			'severity',
			'owner',
			'status',
			'applied_controls',
			'labels'
		],
		body: [
			'ref_id',
			'name',
			'findings_assessment',
			'severity',
			'owner',
			'status',
			'applied_controls',
			'filtering_labels'
		],
		filters: { filtering_labels: LABELS_FILTER }
	},
	incidents: {
		head: [
			'ref_id',
			'name',
			'status',
			'severity',
			'detection',
			'folder',
			'qualifications',
			'updated_at'
		],
		body: [
			'ref_id',
			'name',
			'status',
			'severity',
			'detection',
			'folder',
			'qualifications',
			'updated_at'
		],
		filters: {
			folder: DOMAIN_FILTER,
			qualifications: QUALIFICATION_FILTER,
			status: INCIDENT_STATUS_FILTER,
			detection: INCIDENT_DETECTION_FILTER,
			severity: INCIDENT_SEVERITY_FILTER
		}
	},
	'timeline-entries': {
		head: ['entry_type', 'entry', 'author', 'created_at', 'updated_at', 'timestamp'],
		body: ['entry_type', 'entry', 'author', 'created_at', 'updated_at', 'timestamp']
	},
	campaigns: {
		head: ['name', 'description', 'framework', 'status'],
		body: ['name', 'description', 'framework', 'status']
	},
	'task-templates': {
		head: [
			'name',
			'description',
			'is_recurrent',
			'assigned_to',
			'lastOccurrenceStatus',
			'nextOccurrence'
		],
		body: [
			'name',
			'description',
			'is_recurrent',
			'assigned_to',
			'last_occurrence_status',
			'next_occurrence'
		]
	},
	'task-nodes': {
		head: ['due_date', 'status', 'evidences'],
		body: ['due_date', 'status', 'evidences'],
		filters: {
			status: TASK_STATUS_FILTER
		}
	},
	qualifications: {
		head: ['name', 'abbreviation'],
		body: ['name', 'abbreviation']
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

export const contextMenuActions = {
	'applied-controls': [{ component: ChangeStatus, props: {} }],
	'feared-events': [{ component: SelectObject, props: {} }],
	'ro-to': [{ component: SelectObject, props: {} }],
	stakeholders: [{ component: SelectObject, props: {} }],
	'attack-paths': [{ component: SelectObject, props: {} }],
	'operational-scenarios': [{ component: SelectObject, props: {} }]
};

export const getListViewFields = ({
	key,
	featureFlags = {}
}: {
	key: string;
	featureFlags: Record<string, boolean>;
}) => {
	if (!Object.keys(listViewFields).includes(key)) {
		return { head: [], body: [] };
	}

	const baseEntry = listViewFields[key];
	const model = getModelInfo(key);

	let head = [...baseEntry.head];
	let body = [...baseEntry.body];

	if (model?.flaggedFields) {
		const indicesToPop = body
			.map((field: string, index: number) => {
				const flag = model.flaggedFields?.[field];
				// instead of includes, check if featureFlags[flag] is truthy
				return flag && !featureFlags[flag] ? index : -1;
			})
			.filter((i) => i !== -1);

		head = head.filter((_, index) => !indicesToPop.includes(index));
		body = body.filter((_, index) => !indicesToPop.includes(index));
	}

	return {
		...baseEntry,
		head,
		body
	};
};

function insertField(fields: string[], fieldToInsert: string, afterField: string): string[] {
	const index = fields.indexOf(afterField);
	if (index === -1) return fields;
	const clone = [...fields];
	clone.splice(index + 1, 0, fieldToInsert);
	return clone;
}

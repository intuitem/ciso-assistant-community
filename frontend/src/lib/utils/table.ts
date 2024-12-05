// description of the columns for each ListView

import SelectFilter from '$lib/components/Filters/SelectFilter.svelte';
import type { ComponentType } from 'svelte';
import { LOCALE_DISPLAY_MAP } from './constants';
import type { Row } from '@vincjo/datatables';

interface ListViewFilterConfig {
	component: ComponentType;
	filter?: (columnValue: any, value: any) => boolean;
	getColumn?: (row: Row) => Row[keyof Row];
	filterProps?: (rows: any[], field: string) => { [key: string]: any };
	extraProps?: { [key: string]: any };
	alwaysDisplay?: boolean;
	alwaysDefined?: boolean;
	hide?: boolean;
}

interface ListViewFieldsConfig {
	[key: string]: {
		head: string[];
		body: string[];
		meta?: string[];
		breadcrumb_link_disabled?: boolean;
		filters?: {
			[key: string]: ListViewFilterConfig;
		};
	};
}

const PROJECT_STATUS_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.lc_status,
	extraProps: {
		defaultOptionName: 'status'
	},
	alwaysDisplay: true
};

const DOMAIN_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.folder?.str,
	alwaysDefined: true,
	extraProps: {
		defaultOptionName: 'domain'
	}
};

const LABELS_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => {
		return row.filtering_labels && row.filtering_labels.length > 0
			? row.filtering_labels?.map((filtering_label) => filtering_label.str)
			: [''];
	},
	alwaysDefined: true,
	extraProps: {
		defaultOptionName: 'filtering_labels'
	}
};

const PRIORITY_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.priority,
	alwaysDisplay: true,
	extraProps: {
		defaultOptionName: 'priority'
	}
};

const DOMAIN_FILTER_FROM_PROJECT: ListViewFilterConfig = {
	...DOMAIN_FILTER,
	getColumn: (row) => row.project?.folder.str
};

const PROJECT_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.project?.str,
	extraProps: {
		defaultOptionName: 'project' // Make translations
	}
};

const STATUS_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.status,
	extraProps: {
		defaultOptionName: 'status'
	},
	alwaysDisplay: true
};

const TREATMENT_FILTER: ListViewFilterConfig = {
	// I could make a function just make the code less repeatitive and long for nothing
	component: SelectFilter,
	getColumn: (row) => row.treatment,
	extraProps: {
		defaultOptionName: 'treatment'
	}
};

const STATE_FILTER: ListViewFilterConfig = {
	// I could make a function just make the code less repeatitive and long for nothing
	component: SelectFilter,
	getColumn: (row) => row.state,
	extraProps: {
		defaultOptionName: 'state'
	}
};

const APPROVER_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => {
		if (row.first_name && row.last_name) {
			return `${row.first_name} ${row.last_name}`;
		}
		return row.approver?.str; // This display the email in the approver filter, is this a problem because of email leak risks ?
	},
	extraProps: {
		defaultOptionName: 'approver'
	}
};

const RISK_ASSESSMENT_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.risk_assessment.name,
	extraProps: {
		defaultOptionName: 'riskAssessment'
	}
};

const PROVIDER_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => {
		return row.provider;
	},
	extraProps: {
		defaultOptionName: 'provider'
	}
};

const THREAT_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => (row.threats?.length ? row.threats.map((t) => t.str) : null),
	extraProps: {
		defaultOptionName: 'threat'
	}
};

const ASSET_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => (row.assets?.length ? row.assets.map((t) => t.str) : null),
	extraProps: {
		defaultOptionName: 'asset'
	},
	alwaysDisplay: true
};

const FRAMEWORK_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.framework.ref_id,
	extraProps: {
		defaultOptionName: 'framework' // Make translations
	}
};

const LANGUAGE_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.locales,
	extraProps: {
		defaultOptionName: 'language', // Make translations
		optionLabels: LOCALE_DISPLAY_MAP
	}
};

const ASSET_TYPE_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.type,
	extraProps: {
		defaultOptionName: 'type' // Make translations
	},
	alwaysDisplay: true
};

const CATEGORY_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.category,
	extraProps: {
		defaultOptionName: 'category' // Make translations
	},
	alwaysDisplay: true
};

const CSF_FUNCTION_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => row.csf_function,
	extraProps: {
		defaultOptionName: 'csfFunction' // Make translations
	},
	alwaysDisplay: true
};

const OWNER_FILTER: ListViewFilterConfig = {
	component: SelectFilter,
	getColumn: (row) => {
		const owner = row?.meta?.owner;
		return owner && owner.length ? owner.map((o) => o.str) : null;
	},
	extraProps: {
		defaultOptionName: 'owner'
	},
	alwaysDisplay: true
};
/* const HAS_RISK_MATRIX_FILTER: ListViewFilterConfig = {
  component: CheckboxFilter,
  getColumn: row => {
    return !row.overview.some(
      line => line.startsWith("risk_matrix")
    ); // It would be better to directly have a boolean given by the library data which is set to True when the library has a risk matrix or false otherwise.
  },
  filterProps: (rows: any[],field: string) => new Object(),
  filter: (builtin: boolean, value: boolean): boolean => {
    return value ? !builtin : true;
  },
  extraProps: {
    title: "Only display matrix libraries" // Make translations
  }
}; */

const LIBRARY_TYPE_FILTER = {
	component: SelectFilter,
	getColumn: (row) => {
		const overviewKeys = new Set(row.overview?.map((overviewRow) => overviewRow.split(':')[0]));
		const libraryDatatypeSet = new Set([
			'framework',
			'risk_matrix',
			'threats',
			'requirement_mapping_set',
			'reference_controls'
		]);
		const datatypes = [...libraryDatatypeSet].filter((datatype) => overviewKeys.has(datatype));
		return datatypes;
	},
	extraProps: {
		defaultOptionName: 'objectType'
	},
	alwaysDisplay: true
};

export const listViewFields: ListViewFieldsConfig = {
	folders: {
		head: ['name', 'description', 'parentDomain'],
		body: ['name', 'description', 'parent_folder']
	},
	projects: {
		head: ['ref_id', 'name', 'description', 'domain'],
		body: ['ref_id', 'name', 'description', 'folder'],
		filters: {
			folder: DOMAIN_FILTER,
			lc_status: PROJECT_STATUS_FILTER
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
		head: ['ref_id', 'name', 'riskMatrix', 'description', 'riskScenarios', 'project'],
		body: ['ref_id', 'str', 'risk_matrix', 'description', 'risk_scenarios_count', 'project'],
		filters: {
			folder: { ...DOMAIN_FILTER_FROM_PROJECT, alwaysDisplay: true },
			project: PROJECT_FILTER,
			status: { ...STATUS_FILTER, alwaysDisplay: true }
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
			folder: { ...DOMAIN_FILTER_FROM_PROJECT, alwaysDisplay: true },
			project: { ...PROJECT_FILTER, alwaysDisplay: true },
			treatment: { ...TREATMENT_FILTER, alwaysDisplay: true },
			risk_assessment: RISK_ASSESSMENT_FILTER,
			threats: THREAT_FILTER,
			assets: ASSET_FILTER
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
			status: STATUS_FILTER,
			category: CATEGORY_FILTER,
			csf_function: CSF_FUNCTION_FILTER,
			owner: OWNER_FILTER,
			priority: PRIORITY_FILTER
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
			status: STATUS_FILTER,
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
			folder: { ...DOMAIN_FILTER, alwaysDisplay: true },
			category: CATEGORY_FILTER,
			provider: PROVIDER_FILTER,
			csf_function: CSF_FUNCTION_FILTER
		}
	},
	assets: {
		head: [
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
		head: ['email', 'firstName', 'lastName'],
		body: ['email', 'first_name', 'last_name']
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
		head: ['ref_id', 'name', 'framework', 'description', 'project'],
		body: ['ref_id', 'name', 'framework', 'description', 'project'],
		filters: {
			folder: { ...DOMAIN_FILTER_FROM_PROJECT, alwaysDisplay: true }, // alwaysDisplay shoudln't be mandatory here something is wrong
			project: PROJECT_FILTER,
			framework: FRAMEWORK_FILTER,
			status: STATUS_FILTER
		}
	},
	'requirement-assessments': {
		head: ['name', 'description', 'complianceAssessment'],
		body: ['name', 'description', 'compliance_assessment'],
		breadcrumb_link_disabled: true
	},
	evidences: {
		head: ['name', 'file', 'size', 'description'],
		body: ['name', 'attachment', 'size', 'description'],
		filters: {
			folder: { ...DOMAIN_FILTER, alwaysDisplay: true } // This filter should also be displayed even without alwaysDisplay
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
		head: ['provider', 'name', 'description', 'language', 'overview'],
		body: ['provider', 'name', 'description', 'locales', 'overview'],
		filters: {
			locales: LANGUAGE_FILTER,
			provider: PROVIDER_FILTER,
			objectType: LIBRARY_TYPE_FILTER
		}
	},
	'loaded-libraries': {
		head: ['provider', 'name', 'description', 'language', 'overview'],
		body: ['provider', 'name', 'description', 'locales', 'overview'],
		filters: {
			locales: LANGUAGE_FILTER,
			provider: PROVIDER_FILTER,
			objectType: LIBRARY_TYPE_FILTER
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
		head: ['name', 'description', 'project', 'entity'],
		body: ['name', 'description', 'project', 'entity'],
		filters: {
			project: PROJECT_FILTER,
			status: STATUS_FILTER
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
		head: ['selected', 'assets', 'fearedEvent', 'qualifications', 'gravity'],
		body: ['is_selected', 'assets', 'description', 'qualifications', 'gravity']
	},
	'ro-to': {
		head: [
			'isSelected',
			'riskOrigin',
			'targetObjective',
			'motivation',
			'fearedEvents',
			'pertinence'
		],
		body: [
			'is_selected',
			'risk_origin',
			'target_objective',
			'motivation',
			'feared_events',
			'pertinence'
		]
	},
	stakeholders: {
		head: ['entity', 'category', 'current_criticality', 'applied_controls', 'residual_criticality'],
		body: ['entity', 'category', 'current_criticality', 'applied_controls', 'residual_criticality']
	},
	'attack-paths': {
		head: ['risk_origin', 'target_objective', 'stakeholders', 'attackPath'],
		body: ['risk_origin', 'target_objective', 'stakeholders', 'description']
	},
	'operational-scenarios': {
		head: ['description', 'threats', 'likelihood'],
		body: ['description', 'threats', 'likelihood']
	}
};

import type { urlModel } from './types';
import { BASE_API_URL } from './constants';
import EvidenceFilePreview from '$lib/components/ModelTable/EvidenceFilePreview.svelte';
import LanguageDisplay from '$lib/components/ModelTable/LanguageDisplay.svelte';
import LibraryActions from '$lib/components/ModelTable/LibraryActions.svelte';

type GetOptionsParams = {
	objects: any[];
	suggestions?: any[];
	label?: string;
	value?: string;
};

export const getOptions = ({
	objects,
	suggestions,
	label = 'name',
	value = 'id',
	self = undefined,
	selfSelect = false
}: GetOptionsParams): {
	label: string;
	value: string;
	suggested: boolean;
	self: Record<string, any>;
	selfSelect: boolean;
}[] => {
	const options = objects
		.map((object) => {
			return {
				label: object[label],
				value: object[value],
				suggested: false
			};
		})
		.filter((option) => {
			if (selfSelect) {
				return true;
			}
			return option.value !== self?.id;
		});

	if (suggestions) {
		const suggestedIds = suggestions.map((suggestion) => suggestion[value]);

		const filteredOptions = options.filter((option) => {
			const isSuggested = suggestedIds.includes(option.value);
			if (isSuggested) {
				option.suggested = true;
			}
			return !isSuggested;
		});

		const suggestedOptions = options.filter((option) => option.suggested);
		const reorderedOptions = suggestedOptions.concat(filteredOptions);

		return reorderedOptions;
	}

	return options;
};

interface ForeignKeyField {
	field: string;
	urlModel: urlModel;
	urlParams?: string;
}

interface SelectField {
	field: string;
}

export interface ModelMapEntry {
	name: string;
	verboseName: string;
	verboseNamePlural?: string;
	urlModel?: urlModel;
	foreignKeyFields?: ForeignKeyField[];
	reverseForeignKeyFields?: ForeignKeyField[];
	selectFields?: SelectField[];
	filters?: SelectField[];
	[key: string]: any;
}

type ModelMap = {
	[key: string]: ModelMapEntry;
};

export const URL_MODEL_MAP: ModelMap = {
	folders: {
		name: 'folder',
		verboseName: 'Domain',
		verboseNamePlural: 'Domains',
		// NOTE: urlParams hard-coded for now, but should be dynamic
		foreignKeyFields: [
			{ field: 'parent_folder', urlModel: 'folders', urlParams: 'content_type=GL' }
		],
		reverseForeignKeyFields: [{ field: 'folder', urlModel: 'projects' }]
	},
	projects: {
		name: 'project',
		verboseName: 'Project',
		verboseNamePlural: 'Projects',
		// NOTE: urlParams hard-coded for now, but should be dynamic
		foreignKeyFields: [{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' }],
		selectFields: [{ field: 'lc_status' }],
		reverseForeignKeyFields: [
			{ field: 'project', urlModel: 'risk-assessments' },
			{ field: 'project', urlModel: 'compliance-assessments' }
		],
		filters: [{ field: 'lc_status' }, { field: 'folder' }]
	},
	'risk-matrices': {
		name: 'riskmatrix',
		verboseName: 'Risk matrix',
		verboseNamePlural: 'Risk matrices',
		foreignKeyFields: [{ field: 'folder', urlModel: 'folders' }]
	},
	'risk-assessments': {
		name: 'riskassessment',
		verboseName: 'Risk assessment',
		verboseNamePlural: 'Risk assessments',
		foreignKeyFields: [
			{ field: 'project', urlModel: 'projects' },
			{ field: 'authors', urlModel: 'users' },
			{ field: 'reviewers', urlModel: 'users' },
			{ field: 'risk_matrix', urlModel: 'risk-matrices' },
			{ field: 'risk_scenarios', urlModel: 'risk-scenarios' }
		],
		reverseForeignKeyFields: [{ field: 'risk_assessment', urlModel: 'risk-scenarios' }],
		filters: [{ field: 'project' }, { field: 'auditor' }]
	},
	threats: {
		ref_id: 'ref_id',
		name: 'threat',
		verboseName: 'Threat',
		verboseNamePlural: 'Threats',
		foreignKeyFields: [{ field: 'folder', urlModel: 'folders' }]
	},
	'risk-scenarios': {
		name: 'riskscenario',
		verboseName: 'Risk scenario',
		verboseNamePlural: 'Risk scenarios',
		foreignKeyFields: [
			{ field: 'threats', urlModel: 'threats' },
			{ field: 'risk_assessment', urlModel: 'risk-assessments' },
			{ field: 'assets', urlModel: 'assets' },
			{ field: 'security_measures', urlModel: 'security-measures' },
			{ field: 'project', urlModel: 'projects' },
			{ field: 'risk_matrix', urlModel: 'risk-matrices' },
			{ field: 'auditor', urlModel: 'users' }
		],
		filters: [{ field: 'threats' }, { field: 'risk_assessment' }],
		search: false
	},
	'security-measures': {
		name: 'securitymeasure',
		verboseName: 'Security measure',
		verboseNamePlural: 'Security measures',
		foreignKeyFields: [
			{ field: 'security_function', urlModel: 'security-functions' },
			{ field: 'folder', urlModel: 'folders' },
			{ field: 'evidences', urlModel: 'evidences' }
		],
		selectFields: [{ field: 'status' }, { field: 'category' }, { field: 'effort' }],
		filters: [
			{ field: 'security_function' },
			{ field: 'status' },
			{ field: 'category' },
			{ field: 'effort' },
			{ field: 'folder' }
		]
	},
	policies: {
		name: 'policy',
		verboseName: 'Policy',
		verboseNamePlural: 'Policies',
		foreignKeyFields: [
			{ field: 'security_function', urlModel: 'security-functions', urlParams: 'category=policy' },
			{ field: 'folder', urlModel: 'folders' },
			{ field: 'evidences', urlModel: 'evidences' }
		],
		selectFields: [{ field: 'status' }, { field: 'category' }, { field: 'effort' }],
		filters: [
			{ field: 'security_function' },
			{ field: 'status' },
			{ field: 'effort' },
			{ field: 'folder' }
		]
	},
	'risk-acceptances': {
		name: 'riskacceptance',
		verboseName: 'Risk acceptance',
		verboseNamePlural: 'Risk acceptances',
		foreignKeyFields: [
			{
				field: 'risk_scenarios',
				urlModel: 'risk-scenarios',
				urlParams: '/acceptable'
			},
			{ field: 'folder', urlModel: 'folders' },
			{ field: 'approver', urlModel: 'users', urlParams: 'is_approver=true' }
		],
		filters: [{ field: 'risk_scenarios' }, { field: 'folder' }, { field: 'approver' }]
	},
	'security-functions': {
		ref_id: 'ref_id',
		name: 'securityfunction',
		verboseName: 'Security function',
		verboseNamePlural: 'Security functions',
		foreignKeyFields: [{ field: 'folder', urlModel: 'folders' }],
		selectFields: [{ field: 'category' }],
		filters: [{ field: 'folder' }]
	},
	assets: {
		name: 'asset',
		verboseName: 'Asset',
		verboseNamePlural: 'Assets',
		foreignKeyFields: [
			{ field: 'parent_assets', urlModel: 'assets' },
			{ field: 'folder', urlModel: 'folders' }
		],
		selectFields: [{ field: 'type' }],
		filters: [{ field: 'parent_assets' }, { field: 'folder' }, { field: 'type' }]
	},
	users: {
		name: 'user',
		verboseName: 'User',
		verboseNamePlural: 'Users',
		foreignKeyFields: [{ field: 'user_groups', urlModel: 'user-groups' }],
		filters: []
	},
	'user-groups': {
		name: 'usergroup',
		verboseName: 'User group',
		verboseNamePlural: 'User groups',
		foreignKeyFields: [],
		filters: []
	},
	'role-assignments': {
		name: 'roleassignment',
		verboseName: 'Role assignment',
		verboseNamePlural: 'Role assignments',
		foreignKeyFields: [],
		filters: []
	},
	frameworks: {
		ref_id: 'ref_id',
		name: 'framework',
		verboseName: 'Framework',
		verboseNamePlural: 'Frameworks',
		foreignKeyFields: [
			{
				field: 'folder',
				urlModel: 'folders'
			}
		]
	},
	evidences: {
		name: 'evidence',
		verboseName: 'Evidence',
		verboseNamePlural: 'Evidences',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders' },
			{ field: 'security_measures', urlModel: 'security-measures' },
			{ field: 'requirement_assessments', urlModel: 'requirement-assessments' }
		]
	},
	'compliance-assessments': {
		name: 'complianceassessment',
		verboseName: 'Compliance assessment',
		verboseNamePlural: 'Compliance assessments',
		foreignKeyFields: [
			{ field: 'project', urlModel: 'projects' },
			{ field: 'authors', urlModel: 'users' },
			{ field: 'reviewers', urlModel: 'users' },
			{ field: 'framework', urlModel: 'frameworks' }
		]
	},
	requirements: {
		ref_id: 'ref_id',
		name: 'requirement',
		verboseName: 'Requirement',
		verboseNamePlural: 'Requirements'
	},
	'requirement-assessments': {
		name: 'requirementassessment',
		verboseName: 'Requirement assessment',
		verboseNamePlural: 'Requirement assessments',
		selectFields: [{ field: 'status' }],
		foreignKeyFields: [
			{ field: 'security_measures', urlModel: 'security-measures' },
			{ field: 'evidences', urlModel: 'evidences' },
			{ field: 'compliance_assessment', urlModel: 'compliance-assessments' }
		]
	},
	libraries: {
		name: 'library',
		verboseName: 'Library',
		verboseNamePlural: 'Libraries'
	}
};

export const FIELD_COMPONENT_MAP = {
	evidences: {
		attachment: EvidenceFilePreview
	},
	libraries: {
		locale: LanguageDisplay,
		actions: LibraryActions
	}
};

// Il faut afficher le tag "draft" pour la column name !

interface TagConfig {
	key: string;
	values: {
		[key: string]: {
			text: string;
			cssClasses: string;
		};
	};
}

interface FieldColoredTagMap {
	[key: string]: {
		[key: string]: TagConfig[] | TagConfig;
	};
}

export const FIELD_COLORED_TAG_MAP: FieldColoredTagMap = {
	'risk-assessments': {
		name: {
			key: 'is_draft',
			values: {
				true: { text: 'draft', cssClasses: 'badge bg-blue-200' }
			} // badge bg-blue-200 | bg-blue-500
		}
	},
	'risk-scenarios': {
		name: {
			key: 'treatment',
			values: {
				Open: { text: 'Open', cssClasses: 'badge bg-green-300' },
				Mitigate: { text: 'Mitigate', cssClasses: 'badge bg-lime-200' },
				Accept: { text: 'Accept', cssClasses: 'badge bg-green-200' },
				Avoid: { text: 'Avoid', cssClasses: 'badge bg-red-200' },
				Transfer: { text: 'Transfer', cssClasses: 'badge bg-yellow-300' }
			}
		}
	},
	'compliance-assessments': {
		name: [
			{
				key: 'is_draft',
				values: {
					true: { text: 'draft', cssClasses: 'badge bg-blue-200' }
				}
			},
			{
				key: 'is_obsolete',
				values: {
					true: { text: 'obsolete', cssClasses: 'badge bg-red-300' }
				}
			}
		]
	},
	assets: {
		name: {
			key: 'type',
			values: {
				Primary: { text: 'primary', cssClasses: 'badge bg-blue-200' }
			}
		}
	},
	'security-measures': {
		name: {
			key: 'status',
			values: {
				Open: { text: 'open', cssClasses: 'badge bg-blue-200' },
				'In progress': { text: 'in progress', cssClasses: 'badge bg-green-200' },
				'On hold': { text: 'on hold', cssClasses: 'badge bg-yellow-300' },
				Done: { text: 'done', cssClasses: 'badge bg-red-200' }
			}
		}
	},
	projects: {
		name: {
			key: 'lc_status',
			values: {
				Dropped: { text: 'dropped', cssClasses: 'badge bg-red-200' }
			}
		}
	}
};

export const CUSTOM_MODEL_FETCH_MAP: { [key: string]: (load_data: any) => any } = {
	frameworks: async ({ fetch }) => {
		const endpoint = `${BASE_API_URL}/frameworks/`;
		const res = await fetch(endpoint);
		const response_data = await res.json();
		const frameworks = response_data.results;

		let compliance_assessment_req = null;
		let compliance_assessment_data = null;

		for (const framework of frameworks) {
			compliance_assessment_req = await fetch(
				`${BASE_API_URL}/compliance-assessments/?framework=${framework.id}`
			);
			compliance_assessment_data = await compliance_assessment_req.json();
			framework.compliance_assessments = compliance_assessment_data.count;
		}

		return frameworks;
	}
};

export const urlParamModelVerboseName = (model: string): string => {
	return URL_MODEL_MAP[model]?.verboseName || '';
};

export const urlParamModelForeignKeyFields = (model: string): ForeignKeyField[] => {
	return URL_MODEL_MAP[model]?.foreignKeyFields || [];
};

export const urlParamModelSelectFields = (model: string): SelectField[] => {
	return URL_MODEL_MAP[model]?.selectFields || [];
};

export const getModelInfo = (model: string): ModelMapEntry => {
	const map = URL_MODEL_MAP[model] || {};
	map['urlModel' as urlModel] = model;
	return map;
};

export function processObject(
	data: Record<string, any>,
	regex: RegExp,
	computeReplacement: (matchedString: string) => string
): void {
	for (const key in data) {
		if (!Object.prototype.hasOwnProperty.call(data, key)) continue;

		if (typeof data[key] === 'object' && data[key] !== null) {
			processObject(data[key], regex, computeReplacement); // Recursive call for objects
		} else if (typeof data[key] === 'string') {
			data[key] = data[key].replace(regex, (match: string) => computeReplacement(match)); // Compute replacement for matched strings
		} else if (Array.isArray(data[key])) {
			data[key] = data[key].map(
				(item: any) =>
					typeof item === 'string'
						? item.replace(regex, (match) => computeReplacement(match)) // Compute replacement for matched strings in arrays
						: processObject(item, regex, computeReplacement) // Recursive call for objects in arrays
			);
		}
	}
}

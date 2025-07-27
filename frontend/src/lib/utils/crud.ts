// define the content of forms

import EvidenceFilePreview from '$lib/components/ModelTable/EvidenceFilePreview.svelte';
import LanguageDisplay from '$lib/components/ModelTable/LanguageDisplay.svelte';
import LibraryActions from '$lib/components/ModelTable/LibraryActions.svelte';
import UserGroupNameDisplay from '$lib/components/ModelTable/UserGroupNameDisplay.svelte';
import { type urlModel } from './types';

type GetOptionsParams = {
	objects: any[];
	suggestions?: any[];
	label?: string;
	value?: string;
	extra_fields: string[];
	self?: Record<string, any>;
	selfSelect?: boolean;
};

function getValue(object: { [key: string]: any }, keys: string | string[]) {
	if (typeof keys === 'string') {
		return object[keys];
	}
	let finalValue = object;
	for (const key of keys) {
		finalValue = finalValue[key];
	}
	return finalValue;
}

export const getOptions = ({
	objects,
	suggestions,
	label = 'name',
	value = 'id',
	extra_fields = [],
	self = undefined,
	selfSelect = false
}: GetOptionsParams): {
	label: string;
	value: string;
	suggested: boolean;
	self?: Record<string, any>;
	selfSelect?: boolean;
}[] => {
	const append = (x, y) => (!y ? x : !x || x == '' ? y : x + ' - ' + y);
	const options = objects
		.map((object) => {
			const my_label =
				label != 'auto'
					? (object[label] ?? '')
					: (append(object['ref_id'], object['name'] ? object['name'] : object['description']) ??
						'');
			return {
				label:
					extra_fields.length > 0
						? extra_fields
								.map((field) => getValue(object, field))
								.map((string) => `${string}`)
								.join('/') +
							'/' +
							my_label
						: my_label,
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
	endpointUrl?: string;
	urlParams?: string;
	detail?: boolean;
	detailUrlParams?: string[]; // To prepare possible fetch for foreign keys with detail in generic views
	disableCreate?: boolean;
	disableDelete?: boolean;
}

interface Field {
	keyNameOverride?: string;
	field: string;
	type?: 'date' | 'datetime';
}

interface SelectField {
	field: string;
	detail?: boolean;
	valueType?: 'string' | 'number';
	endpointUrl?: string;
	formNestedField?: string;
}

type FeatureFlag = string;

export interface ModelMapEntry {
	name: string;
	localName: string;
	localNamePlural: string;
	verboseName: string;
	verboseNamePlural?: string;
	urlModel?: urlModel;
	listViewUrlParams?: string;
	flaggedFields?: Record<string, FeatureFlag>;
	detailViewFields?: Field[];
	foreignKeyFields?: ForeignKeyField[];
	reverseForeignKeyFields?: ForeignKeyField[];
	selectFields?: SelectField[];
	fileFields?: string[];
	filters?: SelectField[];
	path?: string;
	endpointUrl?: string;
}

type ModelMap = {
	[key: string]: ModelMapEntry;
};

export const URL_MODEL_MAP: ModelMap = {
	folders: {
		name: 'folder',
		localName: 'domain',
		localNamePlural: 'domains',
		verboseName: 'Domain',
		verboseNamePlural: 'Domains',
		listViewUrlParams: '?content_type=DO&content_type=GL',
		foreignKeyFields: [{ field: 'parent_folder', urlModel: 'folders' }],
		reverseForeignKeyFields: [
			{ field: 'folder', urlModel: 'perimeters' },
			{ field: 'folder', urlModel: 'entities' },
			{ field: 'folder', urlModel: 'assets' }
		]
	},
	perimeters: {
		name: 'perimeter',
		localName: 'perimeter',
		localNamePlural: 'perimeters',
		verboseName: 'Perimeter',
		verboseNamePlural: 'Perimeters',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{ field: 'default_assignee', urlModel: 'users' }
		],
		selectFields: [{ field: 'lc_status' }],
		reverseForeignKeyFields: [
			{ field: 'perimeter', urlModel: 'compliance-assessments' },
			{ field: 'perimeter', urlModel: 'risk-assessments' },
			{ field: 'perimeter', urlModel: 'entity-assessments' },
			{ field: 'perimeters', urlModel: 'campaigns' }
		],
		filters: [{ field: 'lc_status' }, { field: 'folder' }, { field: 'campaigns' }]
	},
	'risk-matrices': {
		name: 'riskmatrix',
		localName: 'riskMatrix',
		localNamePlural: 'riskMatrices',
		verboseName: 'Risk matrix',
		verboseNamePlural: 'Risk matrices',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'library', urlModel: 'libraries' }
		]
	},
	'risk-assessments': {
		name: 'riskassessment',
		localName: 'riskAssessment',
		localNamePlural: 'riskAssessments',
		verboseName: 'Risk assessment',
		verboseNamePlural: 'Risk assessments',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{ field: 'perimeter', urlModel: 'perimeters' },
			{ field: 'authors', urlModel: 'users' },
			{ field: 'reviewers', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'risk_matrix', urlModel: 'risk-matrices' },
			{ field: 'risk_scenarios', urlModel: 'risk-scenarios' },
			{ field: 'ebios_rm_study', urlModel: 'ebios-rm' }
		],
		reverseForeignKeyFields: [{ field: 'risk_assessment', urlModel: 'risk-scenarios' }],
		selectFields: [{ field: 'status' }],
		filters: [{ field: 'perimeter' }, { field: 'auditor' }, { field: 'status' }]
	},
	'risk-assessment_duplicate': {
		name: 'riskassessment',
		localName: 'riskAssessment',
		localNamePlural: 'riskAssessments',
		verboseName: 'Risk assessment',
		verboseNamePlural: 'Risk assessments',
		foreignKeyFields: [{ field: 'perimeter', urlModel: 'perimeters' }]
	},
	threats: {
		name: 'threat',
		localName: 'threat',
		localNamePlural: 'threats',
		verboseName: 'Threat',
		verboseNamePlural: 'Threats',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'filtering_labels', urlModel: 'filtering-labels' }
		]
	},
	'risk-scenarios': {
		name: 'riskscenario',
		localName: 'riskScenario',
		localNamePlural: 'riskScenarios',
		verboseName: 'Risk scenario',
		verboseNamePlural: 'Risk scenarios',
		flaggedFields: {
			inherent_proba: 'inherent_risk',
			inherent_impact: 'inherent_risk',
			inherent_level: 'inherent_risk'
		},
		foreignKeyFields: [
			{ field: 'threats', urlModel: 'threats' },
			{ field: 'risk_assessment', urlModel: 'risk-assessments' },
			{ field: 'assets', urlModel: 'assets' },
			{ field: 'vulnerabilities', urlModel: 'vulnerabilities' },
			{ field: 'applied_controls', urlModel: 'applied-controls' },
			{ field: 'existing_applied_controls', urlModel: 'applied-controls' },
			{ field: 'perimeter', urlModel: 'perimeters' },
			{ field: 'risk_matrix', urlModel: 'risk-matrices' },
			{ field: 'auditor', urlModel: 'users' },
			{ field: 'owner', urlModel: 'users' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions' }
		],
		filters: [{ field: 'threats' }, { field: 'risk_assessment' }, { field: 'owner' }]
	},
	'applied-controls': {
		name: 'appliedcontrol',
		localName: 'appliedControl',
		localNamePlural: 'appliedControls',
		verboseName: 'Applied control',
		verboseNamePlural: 'Applied controls',
		detailViewFields: [
			{ field: 'id' },
			{ field: 'folder' },
			{ field: 'reference_control' },
			{ field: 'category' },
			{ field: 'csf_function' },
			{ field: 'priority' },
			{ field: 'effort' },
			{ field: 'control_impact' },
			{ field: 'cost' },
			{ field: 'status' },
			{ field: 'created_at', type: 'datetime' },
			{ field: 'updated_at', type: 'datetime' },
			{ field: 'ref_id' },
			{ field: 'name' },
			{ field: 'description' },
			{ field: 'eta', type: 'date' },
			{ field: 'owner' },
			{ field: 'expiry_date', type: 'date' },
			{ field: 'link' },
			{ field: 'progress_field' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions' },
			{ field: 'filtering_labels', urlModel: 'filtering-labels' }
		],
		foreignKeyFields: [
			{ field: 'reference_control', urlModel: 'reference-controls' },
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'evidences', urlModel: 'evidences' },
			{ field: 'owner', urlModel: 'users' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions' },
			{ field: 'filtering_labels', urlModel: 'filtering-labels' },
			{ field: 'requirement_assessments', urlModel: 'requirement-assessments' },
			{ field: 'risk_scenarios', urlModel: 'risk-scenarios' },
			{ field: 'assets', urlModel: 'assets' }
		],
		reverseForeignKeyFields: [
			{ field: 'applied_controls', urlModel: 'evidences' },
			{
				field: 'applied_controls',
				urlModel: 'requirement-assessments',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'applied_controls',
				urlModel: 'risk-scenarios',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'applied_controls',
				urlModel: 'findings',
				disableCreate: true,
				disableDelete: true
			},
			{ field: 'applied_controls', urlModel: 'assets', disableCreate: true, disableDelete: true }
		],
		selectFields: [
			{ field: 'status' },
			{ field: 'category' },
			{ field: 'csf_function' },
			{ field: 'effort' },
			{ field: 'control_impact', valueType: 'number' },
			{ field: 'priority' }
		],
		filters: [
			{ field: 'reference_control' },
			{ field: 'status' },
			{ field: 'category' },
			{ field: 'csf_function' },
			{ field: 'effort' },
			{ field: 'control_impact' },
			{ field: 'folder' },
			{ field: 'owner' },
			{ field: 'priority' }
		]
	},
	'applied-controls_duplicate': {
		name: 'appliedcontrol',
		localName: 'appliedControl',
		localNamePlural: 'appliedControls',
		verboseName: 'Applied control',
		verboseNamePlural: 'Applied controls',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' }
		]
	},
	policies: {
		name: 'appliedcontrol',
		localName: 'policy',
		localNamePlural: 'policies',
		verboseName: 'Policy',
		verboseNamePlural: 'Policies',
		foreignKeyFields: [
			{ field: 'reference_control', urlModel: 'reference-controls', urlParams: 'category=policy' },
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'evidences', urlModel: 'evidences' },
			{ field: 'owner', urlModel: 'users' }
		],
		reverseForeignKeyFields: [{ field: 'applied_controls', urlModel: 'evidences' }],
		selectFields: [
			{ field: 'status' },
			{ field: 'csf_function' },
			{ field: 'effort' },
			{ field: 'control_impact', valueType: 'number' },
			{ field: 'priority' }
		],
		filters: [
			{ field: 'reference_control' },
			{ field: 'status' },
			{ field: 'csf_function' },
			{ field: 'effort' },
			{ field: 'control_impact' },
			{ field: 'folder' },
			{ field: 'owner' },
			{ field: 'priority' }
		]
	},
	vulnerabilities: {
		name: 'vulnerability',
		localName: 'vulnerability',
		localNamePlural: 'vulnerabilities',
		verboseName: 'Vulnerability',
		verboseNamePlural: 'Vulnerabilities',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'assets', urlModel: 'assets' },
			{ field: 'applied_controls', urlModel: 'applied-controls' },
			{ field: 'filtering_labels', urlModel: 'filtering-labels' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions' }
		],
		selectFields: [{ field: 'severity', valueType: 'number' }, { field: 'status' }],
		filters: [{ field: 'folder' }, { field: 'filtering_labels' }]
	},
	'filtering-labels': {
		name: 'filteringlabel',
		localName: 'label',
		localNamePlural: 'labels',
		verboseName: 'Label',
		verboseNamePlural: 'Labels'
	},
	'risk-acceptances': {
		name: 'riskacceptance',
		localName: 'riskAcceptance',
		localNamePlural: 'riskAcceptances',
		verboseName: 'Risk acceptance',
		verboseNamePlural: 'Risk acceptances',
		foreignKeyFields: [
			{
				field: 'risk_scenarios',
				urlModel: 'risk-scenarios',
				urlParams: '/acceptable'
			},
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'approver', urlModel: 'users', urlParams: 'is_approver=true' }
		],
		filters: [{ field: 'risk_scenarios' }, { field: 'folder' }, { field: 'approver' }]
	},
	'reference-controls': {
		name: 'referencecontrol',
		localName: 'referenceControl',
		localNamePlural: 'referenceControls',
		verboseName: 'Reference control',
		verboseNamePlural: 'Reference controls',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'filtering_labels', urlModel: 'filtering-labels' }
		],
		selectFields: [{ field: 'category' }, { field: 'csf_function' }],
		filters: [{ field: 'folder' }]
	},
	assets: {
		name: 'asset',
		localName: 'asset',
		localNamePlural: 'assets',
		verboseName: 'Asset',
		verboseNamePlural: 'Assets',
		reverseForeignKeyFields: [
			{
				field: 'assets',
				urlModel: 'compliance-assessments',
				disableCreate: true,
				disableDelete: true
			},
			{ field: 'assets', urlModel: 'vulnerabilities' },
			{ field: 'assets', urlModel: 'solutions' }
		],
		foreignKeyFields: [
			{ field: 'parent_assets', urlModel: 'assets' },
			{ field: 'children_assets', urlModel: 'assets' },
			{ field: 'owner', urlModel: 'users' },
			{ field: 'asset_class', urlModel: 'asset-class' },
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'filtering_labels', urlModel: 'filtering-labels' },
			{ field: 'ebios_rm_studies', urlModel: 'ebios-rm', endpointUrl: 'ebios-rm/studies' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions' }
		],
		selectFields: [{ field: 'type' }, { field: 'asset_class' }],
		filters: [
			{ field: 'parent_assets' },
			{ field: 'folder' },
			{ field: 'asset_class' },
			{ field: 'type' },
			{ field: 'owner' },
			{ field: 'filtering_labels' }
		]
	},
	'asset-class': {
		endpointUrl: 'asset-class',
		name: 'asset-class',
		localName: 'assetClass',
		localNamePlural: 'assetClasses',
		verboseName: 'assetclass',
		verboseNamePlural: 'assetclasses'
	},
	users: {
		name: 'user',
		localName: 'user',
		localNamePlural: 'users',
		verboseName: 'User',
		verboseNamePlural: 'Users',
		foreignKeyFields: [{ field: 'user_groups', urlModel: 'user-groups' }],
		filters: []
	},
	'user-groups': {
		name: 'usergroup',
		localName: 'userGroup',
		localNamePlural: 'userGroups',

		verboseName: 'User group',
		verboseNamePlural: 'User groups',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' }
		],
		filters: []
	},
	'role-assignments': {
		name: 'roleassignment',
		localName: 'roleAssignment',
		localNamePlural: 'roleAssignments',
		verboseName: 'Role assignment',
		verboseNamePlural: 'Role assignments',
		foreignKeyFields: [],
		filters: []
	},
	frameworks: {
		name: 'framework',
		localName: 'framework',
		localNamePlural: 'frameworks',
		verboseName: 'Framework',
		verboseNamePlural: 'Frameworks',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' }
		]
	},
	evidences: {
		name: 'evidence',
		localName: 'evidence',
		localNamePlural: 'evidences',
		verboseName: 'Evidence',
		verboseNamePlural: 'Evidences',
		fileFields: ['attachment'],
		foreignKeyFields: [
			{
				field: 'folder',
				urlModel: 'folders',
				urlParams: 'content_type=DO&content_type=GL&content_type=EN'
			},
			{ field: 'applied_controls', urlModel: 'applied-controls' },
			{ field: 'requirement_assessments', urlModel: 'requirement-assessments' },
			{ field: 'filtering_labels', urlModel: 'filtering-labels' },
			{ field: 'findings', urlModel: 'findings' },
			{ field: 'findings_assessments', urlModel: 'findings-assessments' }
		],
		reverseForeignKeyFields: [
			{
				field: 'evidences',
				urlModel: 'applied-controls',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'evidences',
				urlModel: 'compliance-assessments',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'evidences',
				urlModel: 'requirement-assessments',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'evidences',
				urlModel: 'findings-assessments',
				disableCreate: true,
				disableDelete: true
			},
			{ field: 'evidences', urlModel: 'findings', disableCreate: true, disableDelete: true }
		]
	},
	'compliance-assessments': {
		name: 'complianceassessment',
		localName: 'complianceAssessment',
		localNamePlural: 'complianceAssessments',
		verboseName: 'Compliance assessment',
		verboseNamePlural: 'Compliance assessments',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{ field: 'perimeter', urlModel: 'perimeters' },
			{ field: 'campaign', urlModel: 'campaigns', endpointUrl: 'campaigns' },
			{ field: 'framework', urlModel: 'frameworks' },
			{ field: 'authors', urlModel: 'users' },
			{ field: 'reviewers', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'baseline', urlModel: 'compliance-assessments' },
			{ field: 'ebios_rm_studies', urlModel: 'ebios-rm' },
			{ field: 'assets', urlModel: 'assets' },
			{ field: 'evidences', urlModel: 'evidences' }
		],
		selectFields: [{ field: 'status' }],
		filters: [{ field: 'status' }]
	},
	requirements: {
		name: 'requirement',
		localName: 'requirement',
		localNamePlural: 'requirements',
		verboseName: 'Requirement',
		verboseNamePlural: 'Requirements'
	},
	'requirement-assessments': {
		name: 'requirementassessment',
		localName: 'requirementAssessment',
		localNamePlural: 'requirementAssessments',
		verboseName: 'Requirement assessment',
		verboseNamePlural: 'Requirement assessments',
		selectFields: [{ field: 'status' }, { field: 'result' }],
		foreignKeyFields: [
			{ field: 'applied_controls', urlModel: 'applied-controls' },
			{ field: 'evidences', urlModel: 'evidences' },
			{ field: 'compliance_assessment', urlModel: 'compliance-assessments' },
			{ field: 'security_exceptions', urlModel: 'security-exceptions' }
		]
	},
	'stored-libraries': {
		name: 'storedlibrary',
		localName: 'storedLibrary',
		localNamePlural: 'storedLibraries',
		verboseName: 'stored Library',
		verboseNamePlural: 'stored Libraries'
	},
	'loaded-libraries': {
		name: 'loadedlibrary',
		localName: 'loadedLibrary',
		localNamePlural: 'loadedLibraries',
		verboseName: 'loaded Library',
		verboseNamePlural: 'loaded Libraries'
	},
	'sso-settings': {
		name: 'ssoSettings',
		localName: 'ssoSettings',
		localNamePlural: 'ssoSettings',
		verboseName: 'SSO settings',
		verboseNamePlural: 'SSO settings',
		selectFields: [{ field: 'provider' }]
	},
	'general-settings': {
		name: 'generalSettings',
		localName: 'generalSettings',
		localNamePlural: 'generalSettings',
		verboseName: 'General settings',
		verboseNamePlural: 'General settings',
		selectFields: [{ field: 'security_objective_scale' }]
	},
	'feature-flags': {
		name: 'featureFlags',
		localName: 'featureFlags',
		localNamePlural: 'featureFlags',
		verboseName: 'Feature flag',
		verboseNamePlural: 'Feature flags'
	},
	'requirement-mapping-sets': {
		name: 'requirementmappingset',
		localName: 'requirementMappingSet',
		localNamePlural: 'requirementMappingSets',
		verboseName: 'Requirement mapping set',
		verboseNamePlural: 'Requirement mapping sets',
		foreignKeyFields: [
			{ field: 'source_framework', urlModel: 'frameworks' },
			{ field: 'target_framework', urlModel: 'frameworks' },
			{ field: 'library', urlModel: 'libraries' }
		]
	},
	entities: {
		name: 'entity',
		localName: 'entity',
		localNamePlural: 'entities',
		verboseName: 'Entity',
		verboseNamePlural: 'Entities',
		reverseForeignKeyFields: [
			{ field: 'entity', urlModel: 'entity-assessments' },
			{ field: 'entity', urlModel: 'representatives' },
			{ field: 'provider_entity', urlModel: 'solutions' }
		],
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'owned_folders', urlModel: 'folders', urlParams: 'owned=false' }
		]
	},
	'entity-assessments': {
		name: 'entityassessment',
		localName: 'entityAssessment',
		localNamePlural: 'entityAssessments',
		verboseName: 'Entity assessment',
		verboseNamePlural: 'Entity assessments',
		foreignKeyFields: [
			{ field: 'perimeter', urlModel: 'perimeters' },
			{ field: 'entity', urlModel: 'entities' },
			{ field: 'solutions', urlModel: 'solutions' },
			{ field: 'framework', urlModel: 'frameworks' },
			{ field: 'authors', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'representatives', urlModel: 'users', urlParams: 'is_third_party=true' },
			{ field: 'reviewers', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'evidence', urlModel: 'evidences' },
			{ field: 'compliance_assessment', urlModel: 'compliance-assessments' }
		],
		selectFields: [{ field: 'status' }, { field: 'conclusion' }],
		filters: [{ field: 'status' }]
	},
	solutions: {
		name: 'solution',
		localName: 'solution',
		localNamePlural: 'solutions',
		verboseName: 'Solution',
		verboseNamePlural: 'Solutions',
		foreignKeyFields: [
			{ field: 'provider_entity', urlModel: 'entities' },
			{ field: 'recipient_entity', urlModel: 'entities' },
			{ field: 'assets', urlModel: 'assets' }
		]
	},
	representatives: {
		name: 'representative',
		localName: 'representative',
		localNamePlural: 'representatives',
		verboseName: 'Representative',
		verboseNamePlural: 'Representatives',
		foreignKeyFields: [
			{ field: 'entity', urlModel: 'entities' },
			{ field: 'user', urlModel: 'users' }
		]
	},
	qualifications: {
		name: 'qualification',
		localName: 'qualification',
		localNamePlural: 'qualifications',
		verboseName: 'Qualification',
		verboseNamePlural: 'Qualifications'
	},
	'business-impact-analysis': {
		endpointUrl: 'resilience/business-impact-analysis',
		name: 'businessimpactanalysis',
		localName: 'businessImpactAnalysis',
		localNamePlural: 'businessImpactAnalysis',
		verboseName: 'businessimpactanalysis',
		verboseNamePlural: 'businessimpactanalysis',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{ field: 'perimeter', urlModel: 'perimeters' },
			{ field: 'authors', urlModel: 'users' },
			{ field: 'reviewers', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'risk_matrix', urlModel: 'risk-matrices' }
		],
		reverseForeignKeyFields: [{ field: 'bia', urlModel: 'asset-assessments' }],
		selectFields: [{ field: 'status' }],
		filters: [{ field: 'perimeter' }, { field: 'auditor' }, { field: 'status' }]
	},
	'asset-assessments': {
		endpointUrl: 'resilience/asset-assessments',
		name: 'assetassessment',
		localName: 'assetAssessment',
		localNamePlural: 'assetAssessments',
		verboseName: 'assetassessment',
		verboseNamePlural: 'assetassessments',
		reverseForeignKeyFields: [{ field: 'asset_assessment', urlModel: 'escalation-thresholds' }],
		foreignKeyFields: [
			{ field: 'asset', urlModel: 'assets' },
			{ field: 'folder', urlModel: 'folders' },
			{ field: 'asset_folder', urlModel: 'folders' },
			{ field: 'dependencies', urlModel: 'assets' },
			{ field: 'associated_controls', urlModel: 'applied-controls' },
			{
				field: 'bia',
				urlModel: 'business-impact-analysis',
				endpointUrl: 'business-impact-analysis'
			}
		]
	},
	'escalation-thresholds': {
		endpointUrl: 'resilience/escalation-thresholds',
		name: 'escalationthreshold',
		localName: 'escalationThreshold',
		localNamePlural: 'escalationThresholds',
		verboseName: 'escalationthreshold',
		verboseNamePlural: 'escalationthresholds',
		selectFields: [
			{ field: 'quant_unit' },
			{
				field: 'quali_impact',
				valueType: 'number',
				detail: true,
				endpointUrl: 'resilience/asset-assessments',
				formNestedField: 'asset_assessment'
			} //this is for edit only
		],
		foreignKeyFields: [
			{
				field: 'asset_assessment',
				urlModel: 'asset-assessments',
				endpointUrl: 'asset-assessments'
			}
		],
		detailViewFields: [
			{ field: 'asset_assessment' },
			{ field: 'get_human_pit' },
			{ field: 'qualifications' },
			{ field: 'quali_impact' },
			{ field: 'justification' },
			{ field: 'created_at' },
			{ field: 'updated_at' }
		]
	},
	processings: {
		endpointUrl: 'privacy/processings',
		name: 'processing',
		localName: 'processing',
		localNamePlural: 'processings',
		verboseName: 'processing',
		verboseNamePlural: 'processings',
		selectFields: [{ field: 'status' }, { field: 'legal_basis' }, { field: 'nature' }],
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO&content_type=GL' },
			{ field: 'owner', urlModel: 'users' }
		],
		reverseForeignKeyFields: [
			{ field: 'processing', urlModel: 'personal-data' },
			{ field: 'processing', urlModel: 'data-subjects' },
			{ field: 'processing', urlModel: 'purposes' },
			{ field: 'processing', urlModel: 'data-recipients' },
			{ field: 'processing', urlModel: 'data-contractors' },
			{ field: 'processing', urlModel: 'data-transfers' },
			{
				field: 'processings',
				urlModel: 'applied-controls',
				disableCreate: true,
				disableDelete: true
			}
		],
		detailViewFields: [
			{ field: 'id' },
			{ field: 'name' },
			{ field: 'description' },
			{ field: 'status' },
			{ field: 'legal_basis' },
			{ field: 'dpia_required' },
			{ field: 'dpia_reference' },
			{ field: 'folder' },
			{ field: 'nature' },
			{ field: 'created_at' },
			{ field: 'updated_at' },
			{ field: 'filtering_labels' }
		]
	},
	'processing-natures': {
		endpointUrl: 'privacy/processing-natures',
		name: 'processingnature',
		localName: 'processingNature',
		localNamePlural: 'processingNatures',
		verboseName: 'processing nature',
		verboseNamePlural: 'processing natures'
	},
	purposes: {
		endpointUrl: 'privacy/purposes',
		name: 'purpose',
		localName: 'purpose',
		localNamePlural: 'purposes',
		verboseName: 'purpose',
		verboseNamePlural: 'purposes',
		foreignKeyFields: [{ field: 'processing', urlModel: 'processings', endpointUrl: 'processings' }]
	},
	'personal-data': {
		endpointUrl: 'privacy/personal-data',
		name: 'personaldata',
		localName: 'personalData',
		localNamePlural: 'personalData',
		verboseName: 'personal data',
		verboseNamePlural: 'personal data',
		foreignKeyFields: [
			{ field: 'processing', urlModel: 'processings', endpointUrl: 'processings' }
		],
		selectFields: [{ field: 'category' }, { field: 'deletion_policy' }]
	},
	'data-subjects': {
		endpointUrl: 'privacy/data-subjects',
		name: 'datasubject',
		localName: 'dataSubject',
		localNamePlural: 'dataSubjects',
		verboseName: 'data subject',
		verboseNamePlural: 'data subjects',
		foreignKeyFields: [{ field: 'processing', urlModel: 'processings' }],
		selectFields: [{ field: 'category' }]
	},
	'data-recipients': {
		endpointUrl: 'privacy/data-recipients',
		name: 'datarecipient',
		localName: 'dataRecipient',
		localNamePlural: 'dataRecipients',
		verboseName: 'data recipient',
		verboseNamePlural: 'data recipients',
		foreignKeyFields: [{ field: 'processing', urlModel: 'processings' }],
		selectFields: [{ field: 'category' }]
	},
	'data-contractors': {
		endpointUrl: 'privacy/data-contractors',
		name: 'datacontractor',
		localName: 'dataContractor',
		localNamePlural: 'dataContractors',
		verboseName: 'data contractor',
		verboseNamePlural: 'data contractors',
		foreignKeyFields: [
			{ field: 'processing', urlModel: 'processings' },
			{ field: 'entity', urlModel: 'entities' }
		],
		selectFields: [{ field: 'relationship_type' }, { field: 'country' }]
	},
	'data-transfers': {
		endpointUrl: 'privacy/data-transfers',
		name: 'datatransfer',
		localName: 'dataTransfer',
		localNamePlural: 'dataTransfers',
		verboseName: 'data transfer',
		verboseNamePlural: 'data transfers',
		foreignKeyFields: [
			{ field: 'processing', urlModel: 'processings' },
			{ field: 'entity', urlModel: 'entities' }
		],
		selectFields: [{ field: 'legal_basis' }, { field: 'country' }]
	},
	'ebios-rm': {
		endpointUrl: 'ebios-rm/studies',
		name: 'ebiosrmstudy',
		localName: 'ebiosRMstudy',
		localNamePlural: 'ebiosRmStudies',
		verboseName: 'Ebios RMstudy',
		verboseNamePlural: 'Ebios RMstudy',
		foreignKeyFields: [
			{ field: 'risk_matrix', urlModel: 'risk-matrices' },
			{ field: 'assets', urlModel: 'assets' },
			{ field: 'authors', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'reviewers', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{ field: 'compliance_assessments', urlModel: 'compliance-assessments' },
			{ field: 'reference_entity', urlModel: 'entities' }
		],
		reverseForeignKeyFields: [{ field: 'ebios_rm_studies', urlModel: 'assets' }],
		selectFields: [{ field: 'quotation_method' }]
	},
	'feared-events': {
		endpointUrl: 'ebios-rm/feared-events',
		name: 'fearedevent',
		localName: 'fearedEvent',
		localNamePlural: 'fearedEvents',
		verboseName: 'Feared event',
		verboseNamePlural: 'Feared events',
		foreignKeyFields: [
			{ field: 'ebios_rm_study', urlModel: 'ebios-rm', endpointUrl: 'ebios-rm/studies' },
			{ field: 'assets', urlModel: 'assets', urlParams: 'type=PR&ebios_rm_studies=', detail: true },
			{ field: 'qualifications', urlModel: 'qualifications' }
		],
		selectFields: [{ field: 'gravity', valueType: 'number', detail: true }]
	},
	'ro-to': {
		endpointUrl: 'ebios-rm/ro-to',
		name: 'roto',
		localName: 'roto',
		localNamePlural: 'roto',
		verboseName: 'Ro to',
		verboseNamePlural: 'Ro to',
		foreignKeyFields: [
			{ field: 'ebios_rm_study', urlModel: 'ebios-rm', endpointUrl: 'ebios-rm/studies' },
			{
				field: 'feared_events',
				urlModel: 'feared-events',
				endpointUrl: 'ebios-rm/feared-events',
				urlParams: 'is_selected=true&ebios_rm_study=',
				detail: true
			}
		],
		selectFields: [
			{ field: 'risk-origin' },
			{ field: 'motivation', valueType: 'number' },
			{ field: 'resources', valueType: 'number' },
			{ field: 'activity', valueType: 'number' }
		]
	},
	stakeholders: {
		endpointUrl: 'ebios-rm/stakeholders',
		name: 'stakeholder',
		localName: 'stakeholder',
		localNamePlural: 'stakeholders',
		verboseName: 'Stakeholder',
		verboseNamePlural: 'Stakeholders',
		foreignKeyFields: [
			{ field: 'entity', urlModel: 'entities' },
			{ field: 'applied_controls', urlModel: 'applied-controls' },
			{ field: 'ebios_rm_study', urlModel: 'ebios-rm', endpointUrl: 'ebios-rm/studies' },
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' }
		],
		selectFields: [{ field: 'category' }],
		reverseForeignKeyFields: [
			{
				field: 'stakeholders',
				urlModel: 'applied-controls'
			}
		]
	},
	'strategic-scenarios': {
		endpointUrl: 'ebios-rm/strategic-scenarios',
		name: 'strategicscenario',
		localName: 'strategicScenario',
		localNamePlural: 'strategicScenarios',
		verboseName: 'Strategic scenario',
		verboseNamePlural: 'Strategic scenarios',
		foreignKeyFields: [
			{ field: 'ebios_rm_study', urlModel: 'ebios-rm', endpointUrl: 'ebios-rm/studies' },
			{
				field: 'ro_to_couple',
				urlModel: 'ro-to',
				endpointUrl: 'ebios-rm/ro-to',
				urlParams: 'is_selected=true&used=false&ebios_rm_study=',
				detail: true
			},
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{
				field: 'attack_paths',
				urlModel: 'attack-paths',
				endpointUrl: 'ebios-rm/attack-paths'
			}
		],
		reverseForeignKeyFields: [
			{
				field: 'strategic_scenario',
				urlModel: 'attack-paths',
				endpointUrl: 'ebios-rm/attack-paths'
			}
		]
	},
	'attack-paths': {
		endpointUrl: 'ebios-rm/attack-paths',
		name: 'attackpath',
		localName: 'attackPath',
		localNamePlural: 'attackPaths',
		verboseName: 'Attack path',
		verboseNamePlural: 'Attack paths',
		foreignKeyFields: [
			{
				field: 'stakeholders',
				urlModel: 'stakeholders',
				endpointUrl: 'ebios-rm/stakeholders',
				urlParams: 'is_selected=true&ebios_rm_study=',
				detail: true
			},
			{ field: 'ebios_rm_study', urlModel: 'ebios-rm', endpointUrl: 'ebios-rm/studies' },
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{
				field: 'strategic_scenario',
				urlModel: 'strategic-scenarios',
				endpointUrl: 'ebios-rm/strategic-scenarios',
				urlParams: 'ebios_rm_study=',
				detail: true
			}
		]
	},
	'operational-scenarios': {
		endpointUrl: 'ebios-rm/operational-scenarios',
		name: 'operationalscenario',
		localName: 'operationalScenario',
		localNamePlural: 'operationalScenarios',
		verboseName: 'Operational scenario',
		verboseNamePlural: 'Operational scenarios',
		foreignKeyFields: [
			{ field: 'ebios_rm_study', urlModel: 'ebios-rm' },
			{ field: 'threats', urlModel: 'threats' },
			{
				field: 'attack_path',
				urlModel: 'attack-paths',
				endpointUrl: 'ebios-rm/attack-paths',
				urlParams: 'is_selected=true&used=false&ebios_rm_study=',
				detail: true
			}
		],
		reverseForeignKeyFields: [
			{
				field: 'operational_scenario',
				urlModel: 'operating-modes',
				endpointUrl: 'ebios-rm/operating-modes'
			}
		],
		selectFields: [
			{ field: 'likelihood', valueType: 'number', detail: true, endpointUrl: 'ebios-rm/studies' }
		]
	},
	'elementary-actions': {
		endpointUrl: 'ebios-rm/elementary-actions',
		name: 'elementaryaction',
		localName: 'elementaryAction',
		localNamePlural: 'elementaryActions',
		verboseName: 'Elementary action',
		verboseNamePlural: 'Elementary actions',
		foreignKeyFields: [
			{ field: 'threat', urlModel: 'threats' },
			{ field: 'folder', urlModel: 'folders' }
		],
		selectFields: [{ field: 'attack_stage', valueType: 'number' }, { field: 'icon' }],
		detailViewFields: [
			{ field: 'folder' },
			{ field: 'ref_id' },
			{ field: 'name' },
			{ field: 'description' },
			{ field: 'threat' },
			{ field: 'icon' },
			{ field: 'attack_stage' },
			{ field: 'created_at' },
			{ field: 'updated_at' }
		]
	},
	'operating-modes': {
		endpointUrl: 'ebios-rm/operating-modes',
		name: 'operatingmode',
		localName: 'operatingMode',
		localNamePlural: 'operatingModes',
		verboseName: 'Operating mode',
		verboseNamePlural: 'Operating modes',
		foreignKeyFields: [
			{ field: 'operational_scenario', urlModel: 'operational-scenarios' },
			{ field: 'elementary_actions', urlModel: 'elementary-actions' },
			{ field: 'folder', urlModel: 'folders' }
		],
		selectFields: [{ field: 'likelihood', valueType: 'number', detail: true }],
		reverseForeignKeyFields: [
			{
				field: 'operating_modes',
				urlModel: 'elementary-actions',
				endpointUrl: 'ebios-rm/elementary-actions',
				disableDelete: true
			},
			{
				field: 'operating_mode',
				urlModel: 'kill-chains',
				endpointUrl: 'ebios-rm/kill-chains'
			}
		],
		detailViewFields: [
			{ field: 'ref_id' },
			{ field: 'name' },
			{ field: 'description' },
			{ field: 'operational_scenario' },
			{ field: 'likelihood' },
			{ field: 'created_at' },
			{ field: 'updated_at' }
		]
	},
	'kill-chains': {
		endpointUrl: 'ebios-rm/kill-chains',
		name: 'killchain',
		localName: 'killChain',
		localNamePlural: 'killChains',
		verboseName: 'Kill chain',
		verboseNamePlural: 'Kill chains',
		foreignKeyFields: [
			{ field: 'operating_mode', urlModel: 'operating-modes' },
			{ field: 'elementary_action', urlModel: 'elementary-actions' },
			{ field: 'antecedents', urlModel: 'elementary-actions' }
		],
		selectFields: [{ field: 'logic_operator' }]
	},
	'security-exceptions': {
		name: 'securityexception',
		localName: 'securityException',
		localNamePlural: 'securityExceptions',
		verboseName: 'Security exception',
		verboseNamePlural: 'Security exceptions',
		foreignKeyFields: [
			{ field: 'owners', urlModel: 'users' },
			{ field: 'approver', urlModel: 'users', urlParams: 'is_approver=true' },
			{ field: 'folder', urlModel: 'folders' }
		],
		selectFields: [{ field: 'severity', valueType: 'number' }, { field: 'status' }],
		reverseForeignKeyFields: [
			{
				field: 'security_exceptions',
				urlModel: 'applied-controls',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'security_exceptions',
				urlModel: 'assets',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'security_exceptions',
				urlModel: 'vulnerabilities',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'security_exceptions',
				urlModel: 'requirement-assessments',
				disableCreate: true,
				disableDelete: true
			},
			{
				field: 'security_exceptions',
				urlModel: 'risk-scenarios',
				disableCreate: true,
				disableDelete: true
			}
		]
	},
	'findings-assessments': {
		name: 'findingsassessment',
		localName: 'findingsAssessment',
		localNamePlural: 'findingsAssessments',
		verboseName: 'Findings assessment',
		verboseNamePlural: 'Findings assessments',
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{ field: 'perimeter', urlModel: 'perimeters' },
			{ field: 'authors', urlModel: 'users' },
			{ field: 'reviewers', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'owner', urlModel: 'users', urlParams: 'is_third_party=false' },
			{ field: 'evidences', urlModel: 'evidences' }
		],
		reverseForeignKeyFields: [
			{ field: 'findings_assessment', urlModel: 'findings' },
			{ field: 'findings_assessments', urlModel: 'evidences' }
		],
		selectFields: [{ field: 'status' }, { field: 'category' }]
	},
	findings: {
		name: 'finding',
		localName: 'finding',
		localNamePlural: 'findings',
		verboseName: 'Finding',
		verboseNamePlural: 'Findings',
		foreignKeyFields: [
			{ field: 'findings_assessment', urlModel: 'findings-assessments' },
			{ field: 'applied_controls', urlModel: 'applied-controls' },
			{ field: 'evidences', urlModel: 'evidences' }
		],
		reverseForeignKeyFields: [
			// 	{ field: 'findings', urlModel: 'vulnerabilities' },
			// 	{ field: 'findings', urlModel: 'reference-controls' },
			{ field: 'findings', urlModel: 'applied-controls' },
			{ field: 'findings', urlModel: 'evidences' }
		],
		selectFields: [{ field: 'severity', valueType: 'number' }, { field: 'status' }]
	},
	incidents: {
		name: 'incident',
		localName: 'incident',
		localNamePlural: 'incidents',
		verboseName: 'Incident',
		verboseNamePlural: 'Incidents',
		foreignKeyFields: [
			{ field: 'threats', urlModel: 'threats' },
			{ field: 'assets', urlModel: 'assets' },
			{ field: 'perimeter', urlModel: 'perimeters' },
			{ field: 'owner', urlModel: 'users', urlParams: 'is_third_party=false' }
		],
		reverseForeignKeyFields: [{ field: 'incident', urlModel: 'timeline-entries' }],
		selectFields: [
			{ field: 'severity', valueType: 'number' },
			{ field: 'status' },
			{ field: 'detection' }
		]
	},
	'timeline-entries': {
		name: 'timelineentry',
		localName: 'timelineEntry',
		localNamePlural: 'timelineEntries',
		verboseName: 'Timeline entry',
		verboseNamePlural: 'Timeline entries',
		foreignKeyFields: [
			{ field: 'incident', urlModel: 'incidents' },
			{ field: 'author', urlModel: 'users' }
		],
		selectFields: [{ field: 'entry_type' }],
		reverseForeignKeyFields: [{ field: 'timeline_entries', urlModel: 'evidences' }]
	},
	'task-templates': {
		name: 'tasktemplate',
		localName: 'taskTemplate',
		localNamePlural: 'taskTemplates',
		verboseName: 'Task template',
		verboseNamePlural: 'Task templates',
		selectFields: [{ field: 'status' }],
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders' },
			{ field: 'evidences', urlModel: 'evidences' },
			{ field: 'assigned_to', urlModel: 'users' },
			{ field: 'assets', urlModel: 'assets' },
			{ field: 'applied_controls', urlModel: 'applied-controls' },
			{ field: 'compliance_assessments', urlModel: 'compliance-assessments' },
			{ field: 'risk_assessments', urlModel: 'risk-assessments' },
			{ field: 'findings_assessment', urlModel: 'findings-assessments' }
		],
		reverseForeignKeyFields: [
			{ field: 'task_template', urlModel: 'task-nodes', disableCreate: true, disableDelete: true }
		]
	},
	'task-nodes': {
		name: 'tasknode',
		localName: 'taskNode',
		localNamePlural: 'taskNodes',
		verboseName: 'Task node',
		verboseNamePlural: 'Task nodes',
		selectFields: [{ field: 'status' }],
		foreignKeyFields: [
			{ field: 'task_template', urlModel: 'task-templates' },
			{ field: 'evidences', urlModel: 'evidences' },
			{ field: 'folder', urlModel: 'folders' }
		]
	},
	campaigns: {
		name: 'campaign',
		localName: 'campaign',
		localNamePlural: 'campaigns',
		verboseName: 'Campaign',
		verboseNamePlural: 'Campaigns',
		selectFields: [{ field: 'status' }],
		foreignKeyFields: [
			{ field: 'folder', urlModel: 'folders', urlParams: 'content_type=DO' },
			{ field: 'framework', urlModel: 'frameworks' },
			{ field: 'perimeters', urlModel: 'perimeters' }
		],
		reverseForeignKeyFields: [
			{
				field: 'campaign',
				urlModel: 'compliance-assessments',
				disableCreate: true,
				disableDelete: true
			},
			{ field: 'campaigns', urlModel: 'perimeters', disableCreate: true, disableDelete: true }
		],
		detailViewFields: [
			{ field: 'id' },
			{ field: 'name' },
			{ field: 'description' },
			{ field: 'framework' },
			{ field: 'status' },
			{ field: 'start_date' },
			{ field: 'due_date' },
			{ field: 'created_at' },
			{ field: 'updated_at' }
		],
		filters: [
			{ field: 'status' },
			{ field: 'framework' },
			{ field: 'folder' },
			{ field: 'perimeters' }
		]
	}
};

export const CUSTOM_ACTIONS_COMPONENT = Symbol('CustomActions');

export const FIELD_COMPONENT_MAP = {
	evidences: {
		attachment: EvidenceFilePreview
	},
	'stored-libraries': {
		locales: LanguageDisplay,
		[CUSTOM_ACTIONS_COMPONENT]: LibraryActions
	},
	'loaded-libraries': {
		locales: LanguageDisplay,
		[CUSTOM_ACTIONS_COMPONENT]: LibraryActions
	},
	'user-groups': {
		localization_dict: UserGroupNameDisplay
	}
};

// Il faut afficher le tag "draft" pour la column name !

interface TagConfig {
	text: string;
	cssClasses: string;
}

interface FieldColoredTagMap {
	[key: string]: {
		[key: string]: {
			keys: { [key: string]: { [key: string]: TagConfig } };
			values?: { [key: string]: TagConfig };
		};
	};
}

export const FIELD_COLORED_TAG_MAP: FieldColoredTagMap = {
	policies: {
		name: {
			keys: {
				status: {
					to_do: { text: 'toDo', cssClasses: 'badge bg-blue-200' },
					in_progress: { text: 'inProgress', cssClasses: 'badge bg-yellow-300' },
					active: { text: 'active', cssClasses: 'badge bg-green-200' },
					on_hold: { text: 'onHold', cssClasses: 'badge bg-gray-300' },
					deprecated: { text: 'deprecated', cssClasses: 'badge bg-red-300' },
					'--': { text: 'undefined', cssClasses: 'badge bg-gray-300' }
				},
				priority: {
					P1: { text: '', cssClasses: 'fa-solid fa-flag text-red-500' },
					P2: { text: '', cssClasses: 'fa-solid fa-flag text-orange-500' },
					P3: { text: '', cssClasses: 'fa-solid fa-flag text-blue-500' },
					P4: { text: '', cssClasses: 'fa-solid fa-flag text-gray-500' },
					'--': { text: '', cssClasses: '' }
				}
			}
		}
	},
	'risk-assessments': {
		name: {
			keys: {
				status: {
					planned: { text: 'planned', cssClasses: 'badge bg-indigo-300' },
					in_progress: { text: 'inProgress', cssClasses: 'badge bg-yellow-300' },
					in_review: { text: 'inReview', cssClasses: 'badge bg-cyan-300' },
					done: { text: 'done', cssClasses: 'badge bg-lime-300' },
					deprecated: { text: 'deprecated', cssClasses: 'badge bg-orange-300' }
				}
			}
		}
	},
	'risk-scenarios': {
		name: {
			keys: {
				treatment: {
					open: { text: 'open', cssClasses: 'badge bg-green-300' },
					mitigate: { text: 'mitigate', cssClasses: 'badge bg-lime-200' },
					accept: { text: 'accept', cssClasses: 'badge bg-green-200' },
					avoid: { text: 'avoid', cssClasses: 'badge bg-red-200' },
					transfer: { text: 'transfer', cssClasses: 'badge bg-yellow-300' }
				}
			}
		}
	},
	'compliance-assessments': {
		name: {
			keys: {
				status: {
					planned: { text: 'planned', cssClasses: 'badge bg-indigo-300' },
					in_progress: { text: 'inProgress', cssClasses: 'badge bg-yellow-300' },
					in_review: { text: 'inReview', cssClasses: 'badge bg-cyan-300' },
					done: { text: 'done', cssClasses: 'badge bg-lime-300' },
					deprecated: { text: 'deprecated', cssClasses: 'badge bg-orange-300' }
				}
			}
		}
	},
	assets: {
		name: {
			keys: {
				type: {
					Primary: { text: 'primary', cssClasses: 'badge bg-blue-200' }
				}
			}
		}
	},
	'applied-controls': {
		name: {
			keys: {
				status: {
					to_do: { text: 'toDo', cssClasses: 'badge bg-blue-200' },
					in_progress: { text: 'inProgress', cssClasses: 'badge bg-yellow-300' },
					active: { text: 'active', cssClasses: 'badge bg-green-200' },
					on_hold: { text: 'onHold', cssClasses: 'badge bg-gray-300' },
					deprecated: { text: 'deprecated', cssClasses: 'badge bg-red-300' },
					'--': { text: 'undefined', cssClasses: 'badge bg-gray-300' }
				},
				priority: {
					P1: { text: '', cssClasses: 'fa-solid fa-flag text-red-500' },
					P2: { text: '', cssClasses: 'fa-solid fa-flag text-orange-500' },
					P3: { text: '', cssClasses: 'fa-solid fa-flag text-blue-500' },
					P4: { text: '', cssClasses: 'fa-solid fa-flag text-gray-500' },
					'--': { text: '', cssClasses: '' }
				}
			}
		}
	},
	perimeters: {
		name: {
			keys: {
				lc_status: {
					Dropped: { text: 'dropped', cssClasses: 'badge bg-red-200' }
				}
			}
		}
	},
	users: {
		email: {
			keys: {
				keep_local_login: {
					true: { text: 'Local', cssClasses: 'badge bg-violet-200' }
				},
				is_third_party: {
					true: { text: 'Third party', cssClasses: 'badge bg-stone-200' }
				}
			}
		}
	}
};

export const getModelInfo = (model: urlModel | string): ModelMapEntry => {
	const baseModel = model.split('_')[0];
	const map = URL_MODEL_MAP[model] || URL_MODEL_MAP[baseModel] || {};
	// The urlmodel of {model}_duplicate must be {model}
	map['urlModel'] = baseModel;
	return map;
};

export const urlParamModelVerboseName = (model: string): string => {
	const modelInfo = getModelInfo(model);
	return modelInfo?.localName || modelInfo?.verboseName || model;
};

export const urlParamModelForeignKeyFields = (model: string): ForeignKeyField[] => {
	return URL_MODEL_MAP[model]?.foreignKeyFields || [];
};

export const urlParamModelSelectFields = (model: string): SelectField[] => {
	return URL_MODEL_MAP[model]?.selectFields || [];
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

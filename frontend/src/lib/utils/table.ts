import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
import type { ComponentType } from 'svelte';
import type { Option } from 'svelte-multiselect';

import ChangeStatus from '$lib/components/ContextMenu/applied-controls/ChangeStatus.svelte';
import ChangeImpact from '$lib/components/ContextMenu/applied-controls/ChangeImpact.svelte';
import ChangeEffort from '$lib/components/ContextMenu/applied-controls/ChangeEffort.svelte';
import EvidenceChangeStatus from '$lib/components/ContextMenu/evidences/ChangeStatus.svelte';
import { getModelInfo } from './crud';
import SelectObject from '$lib/components/ContextMenu/ebios-rm/SelectObject.svelte';
import ChangePriority from '$lib/components/ContextMenu/applied-controls/ChangePriority.svelte';

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

const SOLUTION_CRITICALITY_OPTIONS = [
	{ label: '1', value: '1' },
	{ label: '2', value: '2' },
	{ label: '3', value: '3' },
	{ label: '4', value: '4' }
];

const ENTITY_CRITICALITY_OPTIONS = [
	{ label: '1', value: '1' },
	{ label: '2', value: '2' },
	{ label: '3', value: '3' },
	{ label: '4', value: '4' }
];
const YES_NO_UNSET_OPTIONS = [
	{ label: 'YES', value: 'YES' },
	{ label: 'NO', value: 'NO' },
	{ label: '--', value: '--' }
];

const RISK_STAGE_OPTIONS = [
	{ label: 'Inherent', value: 'inherent' },
	{ label: 'Current', value: 'current' },
	{ label: 'Residual', value: 'residual' }
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

const ACCREDITATION_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'terminologies?field_path=accreditation.status',
		optionsLabelField: 'name',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const ACCREDITATION_CATEGORY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'terminologies?field_path=accreditation.category',
		optionsLabelField: 'name',
		label: 'category',
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
		options: [
			{ label: '--', value: '--' },
			{ label: 'planned', value: 'planned' },
			{ label: 'in_progress', value: 'in_progress' },
			{ label: 'in_review', value: 'in_review' },
			{ label: 'done', value: 'done' },
			{ label: 'deprecated', value: 'deprecated' }
		],
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const QUANT_RISK_SCENARIO_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		options: [
			{ label: '--', value: '--' },
			{ label: 'draft', value: 'draft' },
			{ label: 'open', value: 'open' },
			{ label: 'mitigate', value: 'mitigate' },
			{ label: 'accept', value: 'accept' },
			{ label: 'transfer', value: 'transfer' }
		],
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};
const RISK_STAGE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'risk_stage',
		options: RISK_STAGE_OPTIONS,
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
const ENTITY_ASSESSMENT_CONCLUSION_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'entity-assessments/conclusion',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'conclusion',
		browserCache: 'force-cache',
		multiple: true
	}
};

const REQUIREMENT_ASSESSMENT_RESULT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'requirement-assessments/result',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'result',
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

const APPLIED_CONTROL_IMPACT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'applied-controls/control_impact',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'controlImpact',
		browserCache: 'force-cache',
		multiple: true
	}
};

const APPLIED_CONTROL_EFFORT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'applied-controls/effort',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'effort',
		browserCache: 'force-cache',
		multiple: true
	}
};

const RISK_TOLERANCE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'withinTolerance',
		options: YES_NO_UNSET_OPTIONS,
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

const CAMPAIGN_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'campaigns/status',
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
const FINDINGS_SEVERITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'findings/severity',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'severity',
		browserCache: 'force-cache',
		multiple: true
	}
};
const FINDINGS_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'findings/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};
const EXCEPTION_SEVERITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'security-exceptions/severity',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'severity',
		browserCache: 'force-cache',
		multiple: true
	}
};
const EXCEPTION_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'security-exceptions/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};
const PROCESSING_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'processings/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};
const LEGAL_BASIS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'purposes/legal_basis',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'legalBasis',
		browserCache: 'force-cache',
		multiple: true
	}
};
const PROCESSING_NATURE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'processing-natures',
		label: 'nature',
		browserCache: 'force-cache',
		multiple: true
	}
};
const ORGANISATION_OBJECTIVE_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'organisation-objectives/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};
const ORGANISATION_OBJECTIVE_HEALTH_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'organisation-objectives/health',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'health',
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

const REFERENCE_CONTROL_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'referenceControl',
		optionsEndpoint: 'reference-controls',
		multiple: true
	}
};

const COMPLIANCE_ASSESSMENT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'complianceAssessment',
		optionsEndpoint: 'compliance-assessments',
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

const SOLUTION_CRITICALITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'criticality',
		options: SOLUTION_CRITICALITY_OPTIONS,
		multiple: true
	}
};

const ENTITY_CRITICALITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'criticality',
		options: ENTITY_CRITICALITY_OPTIONS,
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

const IS_RECURRENT_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'is_recurrent',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const TASK_TEMPLATE_ASSIGNED_TO_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'assigned_to',
		optionsLabelField: 'email',
		optionsValueField: 'id',
		optionsEndpoint: 'task-templates/assigned_to',
		multiple: true
	}
};

const USER_IS_ACTIVE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'is_active',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const USER_IS_THIRD_PARTY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'is_third_party',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const IS_ASSESSABLE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'assessable',
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

const ENTITY_RELATIONSHIP_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'terminologies?field_path=entity.relationship',
		optionsLabelField: 'name',
		label: 'relationship',
		browserCache: 'force-cache',
		multiple: true
	}
};

const ACCREDITATION_AUTHORITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'authority',
		optionsEndpoint: 'entities?relationship__name=accreditation_authority',
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
		options: [
			{ label: '1', value: 1 },
			{ label: '2', value: 2 },
			{ label: '3', value: 3 },
			{ label: '4', value: 4 }
		],
		multiple: true,
		translateOptions: false
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

const FINDINGS_ASSESSMENTS_CATEGORY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'category',
		optionsEndpoint: 'findings-assessments/category',
		multiple: true,
		optionsLabelField: 'label',
		browserCache: 'force-cache',
		optionsValueField: 'value'
	}
};

const STAKEHOLDER_CATEGORY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'terminologies?field_path=entity.relationship',
		optionsLabelField: 'name',
		label: 'category',
		browserCache: 'force-cache',
		multiple: true
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

const FINDINGS_OWNER_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'owner',
		optionsLabelField: 'email',
		optionsValueField: 'id',
		optionsEndpoint: 'findings/owner',
		multiple: true
	}
};

const LAST_OCCURENCE_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'last_occurrence_status',
		optionsEndpoint: 'task-templates/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		multiple: true
	}
};

const NEXT_OCCURENCE_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'next_occurrence_status',
		optionsEndpoint: 'task-templates/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
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

const IS_ASSIGNED_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'isAssigned',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const FIELD_PATH_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'field_path',
		optionsEndpoint: 'terminologies/field_path',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		multiple: true
	}
};

const BUILTIN_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'builtin',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const IS_VISIBLE_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'is_visible',
		options: YES_NO_OPTIONS,
		multiple: true
	}
};

const EVIDENCE_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'status',
		optionsEndpoint: 'evidences/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		browserCache: 'force-cache',
		multiple: true
	}
};

const EVIDENCE_OWNER_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		label: 'owner',
		optionsLabelField: 'email',
		optionsValueField: 'id',
		optionsEndpoint: 'evidences/owner',
		multiple: true
	}
};

const VULNERABILITY_STATUS_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'vulnerabilities/status',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'status',
		browserCache: 'force-cache',
		multiple: true
	}
};

const VULNERABILITY_SEVERITY_FILTER: ListViewFilterConfig = {
	component: AutocompleteSelect,
	props: {
		optionsEndpoint: 'vulnerabilities/severity',
		optionsLabelField: 'label',
		optionsValueField: 'value',
		label: 'severity',
		browserCache: 'force-cache',
		multiple: true
	}
};

export const listViewFields = {
	folders: {
		head: ['name', 'description', 'parentDomain', 'labels'],
		body: ['name', 'description', 'parent_folder', 'filtering_labels'],
		filters: {
			filtering_labels: LABELS_FILTER
		}
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
			filtering_labels: LABELS_FILTER,
			status: VULNERABILITY_STATUS_FILTER,
			severity: VULNERABILITY_SEVERITY_FILTER
		}
	},
	'risk-assessments': {
		head: ['ref_id', 'name', 'riskMatrix', 'status', 'riskScenarios', 'perimeter'],
		body: ['ref_id', 'str', 'risk_matrix', 'status', 'risk_scenarios_count', 'perimeter'],
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
			'withinTolerance',
			'extraAppliedControls',
			'residualLevel',
			'treatment',
			'riskAssessment',
			'control_impact',
			'effort'
		],
		body: [
			'ref_id',
			'threats',
			'name',
			'inherent_level',
			'existing_applied_controls',
			'current_level',
			'within_tolerance',
			'applied_controls',
			'residual_level',
			'treatment',
			'risk_assessment',
			'control_impact',
			'effort'
		],
		filters: {
			folder: DOMAIN_FILTER,
			perimeter: PERIMETER_FILTER,
			treatment: TREATMENT_FILTER,
			risk_assessment: RISK_ASSESSMENT_FILTER,
			threats: THREAT_FILTER,
			assets: ASSET_FILTER,
			current_level: CURRENT_RISK_LEVEL_FILTER,
			residual_level: RESIDUAL_RISK_LEVEL_FILTER,
			within_tolerance: RISK_TOLERANCE_FILTER,
			control_impact: APPLIED_CONTROL_IMPACT_FILTER,
			effort: APPLIED_CONTROL_EFFORT_FILTER
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
		head: ['ref_id', 'name', 'priority', 'status', 'category', 'eta', 'domain', 'owner', 'labels'],
		body: [
			'ref_id',
			'name',
			'priority',
			'status',
			'category',
			'eta',
			'folder',
			'owner',
			'filtering_labels'
		],
		filters: {
			folder: DOMAIN_FILTER,
			status: APPLIED_CONTROL_STATUS_FILTER,
			category: REFERENCE_CONTROL_CATEGORY_FILTER,
			csf_function: CSF_FUNCTION_FILTER,
			priority: PRIORITY_FILTER,
			effort: EFFORT_FILTER,
			control_impact: APPLIED_CONTROL_IMPACT_FILTER,
			filtering_labels: LABELS_FILTER,
			reference_control: REFERENCE_CONTROL_FILTER,
			eta__lte: undefined,
			is_assigned: IS_ASSIGNED_FILTER,
			owner: OWNER_FILTER
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
			'owner',
			'domain',
			'labels'
		],
		body: [
			'ref_id',
			'name',
			'type',
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
	'asset-class': {
		head: ['name', 'description'],
		body: ['name', 'description']
	},
	users: {
		head: [
			'email',
			'firstName',
			'lastName',
			'userGroups',
			'isActive',
			'keep_local_login',
			'is_third_party',
			'hasMfaEnabled'
		],
		body: [
			'email',
			'first_name',
			'last_name',
			'user_groups',
			'is_active',
			'keep_local_login',
			'is_third_party',
			'has_mfa_enabled'
		],
		filters: {
			is_active: USER_IS_ACTIVE_FILTER,
			is_third_party: USER_IS_THIRD_PARTY_FILTER
		}
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
		head: ['assessable', 'name', 'description', 'complianceAssessment', 'perimeter', 'result'],
		body: ['assessable', 'name', 'description', 'compliance_assessment', 'perimeter', 'result'],
		breadcrumb_link_disabled: true,
		filters: {
			compliance_assessment: COMPLIANCE_ASSESSMENT_FILTER,
			requirement__assessable: IS_ASSESSABLE_FILTER,
			result: REQUIREMENT_ASSESSMENT_RESULT_FILTER,
			compliance_assessment__perimeter: PERIMETER_FILTER
		}
	},
	evidences: {
		head: ['name', 'file', 'folder', 'owner', 'status', 'updatedAt', 'labels'],
		body: ['name', 'attachment', 'folder', 'owner', 'status', 'updated_at', 'filtering_labels'],
		filters: {
			folder: DOMAIN_FILTER,
			filtering_labels: LABELS_FILTER,
			status: EVIDENCE_STATUS_FILTER,
			owner: EVIDENCE_OWNER_FILTER
		}
	},
	'evidence-revisions': {
		head: ['version', 'evidence', 'file', 'size', 'updatedAt'],
		body: ['version', 'evidence', 'attachment', 'size', 'updated_at'],
		filters: {
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
		body: ['provider', 'name', 'description', 'locales', 'objects_meta']
	},
	'stored-libraries': {
		head: ['provider', 'ref_id', 'name', 'description', 'language', 'overview', 'publication_date'],
		body: [
			'provider',
			'ref_id',
			'name',
			'description',
			'locales',
			'objects_meta',
			'publication_date'
		],
		filters: {
			locale: LANGUAGE_FILTER,
			provider: PROVIDER_FILTER,
			object_type: LIBRARY_TYPE_FILTER,
			mapping_suggested: MAPPING_SUGGESTED_FILTER
		}
	},
	'loaded-libraries': {
		head: ['provider', 'ref_id', 'name', 'description', 'language', 'overview', 'publication_date'],
		body: [
			'provider',
			'ref_id',
			'name',
			'description',
			'locales',
			'objects_meta',
			'publication_date'
		],
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
		head: ['name', 'description', 'domain', 'relationship', 'ownedFolders'],
		body: ['name', 'description', 'folder', 'relationship', 'owned_folders'],
		filters: {
			folder: DOMAIN_FILTER,
			relationship: ENTITY_RELATIONSHIP_FILTER
		}
	},
	'entity-assessments': {
		head: ['name', 'entity', 'perimeter', 'status', 'dueDate', 'criticality', 'conclusion'],
		body: ['name', 'entity', 'perimeter', 'status', 'due_date', 'criticality', 'conclusion'],
		filters: {
			perimeter: PERIMETER_FILTER,
			entity: ENTITY_FILTER,
			status: COMPLIANCE_ASSESSMENT_STATUS_FILTER,
			criticality: ENTITY_CRITICALITY_FILTER,
			conclusion: ENTITY_ASSESSMENT_CONCLUSION_FILTER
		}
	},
	solutions: {
		head: ['name', 'description', 'providerEntity', 'recipientEntity', 'criticality'],
		body: ['name', 'description', 'provider_entity', 'recipient_entity', 'criticality'],
		filters: {
			provider_entity: ENTITY_FILTER,
			criticality: SOLUTION_CRITICALITY_FILTER
		}
	},
	representatives: {
		head: ['email', 'entity', 'role'],
		body: ['email', 'entity', 'role'],
		filters: {
			entity: ENTITY_FILTER
		}
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
			'childrenAssets',
			'extraDependencies',
			'associatedControls',
			'recoveryDocumented',
			'recoveryTested',
			'recoveryTargetsMet'
		],
		body: [
			'asset',
			'asset_folder',
			'bia',
			'children_assets',
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
		head: ['name', 'description', 'status', 'processingNature', 'labels', 'folder'],
		body: ['name', 'description', 'status', 'nature', 'filtering_labels', 'folder'],
		filters: {
			folder: DOMAIN_FILTER,
			status: PROCESSING_STATUS_FILTER,
			nature: PROCESSING_NATURE_FILTER,
			filtering_labels: LABELS_FILTER
		}
	},
	'right-requests': {
		head: ['refId', 'name', 'requestType', 'status', 'owner', 'requestedOn', 'dueDate', 'folder'],
		body: [
			'ref_id',
			'name',
			'request_type',
			'status',
			'owner',
			'requested_on',
			'due_date',
			'folder'
		],
		filters: {
			folder: DOMAIN_FILTER,
			request_type: {
				component: AutocompleteSelect,
				props: {
					optionsEndpoint: 'right-requests/request_type',
					optionsLabelField: 'label',
					optionsValueField: 'value',
					label: 'requestType',
					multiple: true
				}
			},
			status: {
				component: AutocompleteSelect,
				props: {
					optionsEndpoint: 'right-requests/status',
					optionsLabelField: 'label',
					optionsValueField: 'value',
					label: 'status',
					multiple: true
				}
			},
			processings: {
				component: AutocompleteSelect,
				props: {
					optionsEndpoint: 'processings',
					label: 'processings',
					multiple: true
				}
			}
		}
	},
	'data-breaches': {
		head: [
			'refId',
			'name',
			'discoveredOn',
			'breachType',
			'riskLevel',
			'status',
			'affectedSubjectsCount',
			'folder'
		],
		body: [
			'ref_id',
			'name',
			'discovered_on',
			'breach_type',
			'risk_level',
			'status',
			'affected_subjects_count',
			'folder'
		],
		filters: {
			folder: DOMAIN_FILTER,
			breach_type: {
				component: AutocompleteSelect,
				props: {
					optionsEndpoint: 'data-breaches/breach_type',
					optionsLabelField: 'label',
					optionsValueField: 'value',
					label: 'breachType',
					multiple: true
				}
			},
			risk_level: {
				component: AutocompleteSelect,
				props: {
					optionsEndpoint: 'data-breaches/risk_level',
					optionsLabelField: 'label',
					optionsValueField: 'value',
					label: 'riskLevel',
					multiple: true
				}
			},
			status: {
				component: AutocompleteSelect,
				props: {
					optionsEndpoint: 'data-breaches/status',
					optionsLabelField: 'label',
					optionsValueField: 'value',
					label: 'status',
					multiple: true
				}
			},
			affected_processings: {
				component: AutocompleteSelect,
				props: {
					optionsEndpoint: 'processings',
					label: 'affectedProcessings',
					multiple: true
				}
			}
		}
	},
	purposes: {
		head: ['name', 'description', 'legalBasis', 'processing'],
		body: ['name', 'description', 'legal_basis', 'processing'],
		filters: {
			processing: PROCESSING_FILTER,
			legal_basis: LEGAL_BASIS_FILTER
		}
	},
	'personal-data': {
		head: ['processing', 'name', 'category', 'isSensitive', 'retention', 'deletionPolicy'],
		body: ['processing', 'name', 'category', 'is_sensitive', 'retention', 'deletion_policy'],
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
		head: ['name', 'description', 'domain', 'quotationMethod'],
		body: ['name', 'description', 'folder', 'quotation_method'],
		filters: {
			folder: DOMAIN_FILTER
		}
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
			category: STAKEHOLDER_CATEGORY_FILTER
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
		head: [
			'is_selected',
			'attackPath',
			'operatingModes',
			'operatingModesDescription',
			'likelihood'
		],
		body: [
			'is_selected',
			'attack_path',
			'operating_modes',
			'operating_modes_description',
			'likelihood'
		],
		filters: {
			threats: THREAT_FILTER,
			likelihood: RISK_PROBABILITY_FILTER,
			is_selected: IS_SELECTED_FILTER
		}
	},
	'elementary-actions': {
		head: ['ref_id', 'folder', '', 'name', 'attack_stage', 'threat'],
		body: ['ref_id', 'folder', 'icon_fa_class', 'name', 'attack_stage', 'threat']
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
		head: [
			'ref_id',
			'name',
			'severity',
			'status',
			'expiration_date',
			'domain',
			'associatedObjectsCount'
		],
		body: [
			'ref_id',
			'name',
			'severity',
			'status',
			'expiration_date',
			'folder',
			'associated_objects_count'
		],
		filters: {
			folder: DOMAIN_FILTER,
			severity: EXCEPTION_SEVERITY_FILTER,
			status: EXCEPTION_STATUS_FILTER
		}
	},
	'findings-assessments': {
		head: ['ref_id', 'name', 'category', 'evidences', 'findings', 'perimeter'],
		body: ['ref_id', 'name', 'category', 'evidences', 'findings_count', 'perimeter'],
		filters: {
			folder: DOMAIN_FILTER,
			perimeter: PERIMETER_FILTER,
			category: FINDINGS_ASSESSMENTS_CATEGORY_FILTER
		}
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
		filters: {
			filtering_labels: LABELS_FILTER,
			severity: FINDINGS_SEVERITY_FILTER,
			status: FINDINGS_STATUS_FILTER,
			owner: FINDINGS_OWNER_FILTER
		}
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
			'entities',
			'reportedAt',
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
			'entities',
			'reported_at',
			'updated_at'
		],
		filters: {
			folder: DOMAIN_FILTER,
			qualifications: QUALIFICATION_FILTER,
			entities: ENTITY_FILTER,
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
		head: ['name', 'description', 'frameworks', 'status'],
		body: ['name', 'description', 'frameworks', 'status'],
		filters: {
			status: CAMPAIGN_STATUS_FILTER,
			frameworks: FRAMEWORK_FILTER
		}
	},
	'organisation-objectives': {
		head: ['refId', 'name', 'domain', 'status', 'health', 'dueDate', 'assignee'],
		body: ['ref_id', 'name', 'folder', 'status', 'health', 'due_date', 'assigned_to'],
		filters: {
			folder: DOMAIN_FILTER,
			status: ORGANISATION_OBJECTIVE_STATUS_FILTER,
			health: ORGANISATION_OBJECTIVE_HEALTH_FILTER
		}
	},
	'organisation-issues': {
		head: ['refId', 'name', 'category', 'origin', 'domain'],
		body: ['ref_id', 'name', 'category', 'origin', 'folder'],
		filters: {
			folder: DOMAIN_FILTER
		}
	},
	'quantitative-risk-studies': {
		head: ['name', 'description', 'status', 'domain'],
		body: ['name', 'description', 'status', 'folder'],
		filters: {
			folder: DOMAIN_FILTER,
			status: RISK_ASSESSMENT_STATUS_FILTER
		}
	},
	'quantitative-risk-scenarios': {
		head: [
			'isSelected',
			'ref_id',
			'name',
			'quantitativeRiskStudy',
			'assets',
			'threats',
			'qualifications',
			'currentAleDisplay',
			'residualAleDisplay',
			'status'
		],
		body: [
			'is_selected',
			'ref_id',
			'name',
			'quantitative_risk_study',
			'assets',
			'threats',
			'qualifications',
			'current_ale_display',
			'residual_ale_display',
			'status'
		],
		filters: {
			status: QUANT_RISK_SCENARIO_STATUS_FILTER,
			assets: ASSET_FILTER,
			threats: THREAT_FILTER,
			is_selected: IS_SELECTED_FILTER
		}
	},
	'quantitative-risk-hypotheses': {
		head: [
			'ref_id',
			'name',
			'riskStage',
			'simulationParameters',
			'lecChart',
			'ale',
			'addedAppliedControls',
			'treatmentCost',
			'rocDisplay',
			'isSelected'
		],
		body: [
			'ref_id',
			'name',
			'risk_stage',
			'simulation_parameters_display',
			'lec_data',
			'ale_display',
			'added_applied_controls',
			'treatment_cost_display',
			'roc_display',
			'is_selected'
		],
		filters: {
			is_selected: {
				component: AutocompleteSelect,
				props: {
					label: 'is_selected',
					options: YES_NO_OPTIONS,
					multiple: true
				}
			},
			risk_stage: RISK_STAGE_FILTER
		}
	},
	'task-templates': {
		head: [
			'refId',
			'name',
			'is_recurrent',
			'assigned_to',
			'lastOccurrenceStatus',
			'nextOccurrence',
			'nextOccurrenceStatus',
			'folder'
		],
		body: [
			'ref_id',
			'name',
			'is_recurrent',
			'assigned_to',
			'last_occurrence_status',
			'next_occurrence',
			'next_occurrence_status',
			'folder'
		],
		filters: {
			folder: DOMAIN_FILTER,
			assigned_to: TASK_TEMPLATE_ASSIGNED_TO_FILTER,
			is_recurrent: IS_RECURRENT_FILTER,
			last_occurrence_status: LAST_OCCURENCE_STATUS_FILTER,
			next_occurrence_status: NEXT_OCCURENCE_STATUS_FILTER
		}
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
	terminologies: {
		head: ['field_path', 'name', 'description', 'translations', 'is_visible'],
		body: ['field_path', 'name', 'description', 'translations', 'is_visible'],
		filters: {
			field_path: FIELD_PATH_FILTER,
			builtin: BUILTIN_FILTER,
			is_visible: IS_VISIBLE_FILTER
		}
	},
	'generic-collections': {
		head: ['ref_id', 'name', 'description', 'labels', 'folder'],
		body: ['ref_id', 'name', 'description', 'filtering_labels', 'folder'],
		filters: {
			folder: DOMAIN_FILTER,
			filtering_labels: LABELS_FILTER
		}
	},
	accreditations: {
		head: ['ref_id', 'name', 'category', 'status', 'authority', 'author', 'expiry_date', 'folder'],
		body: ['ref_id', 'name', 'category', 'status', 'authority', 'author', 'expiry_date', 'folder'],
		filters: {
			folder: DOMAIN_FILTER,
			status: ACCREDITATION_STATUS_FILTER,
			category: ACCREDITATION_CATEGORY_FILTER,
			authority: ACCREDITATION_AUTHORITY_FILTER,
			filtering_labels: LABELS_FILTER
		}
	},
	extra: {
		filters: {
			risk: undefined,
			probability: undefined,
			impact: undefined,
			likelihood: undefined,
			gravity: undefined
		},
		body: ['users']
	}
} as const satisfies ListViewFieldsConfig;

export type FilterKeys = {
	[K in keyof typeof listViewFields]: (typeof listViewFields)[K] extends { filters: infer F }
		? keyof F
		: never;
}[keyof typeof listViewFields];

export const contextMenuActions = {
	'applied-controls': [
		{ component: ChangeStatus, props: {} },
		{ component: ChangeImpact, props: {} },
		{ component: ChangeEffort, props: {} },
		{ component: ChangePriority, props: {} }
	],
	evidences: [{ component: EvidenceChangeStatus, props: {} }],
	'feared-events': [{ component: SelectObject, props: {} }],
	'ro-to': [{ component: SelectObject, props: {} }],
	stakeholders: [{ component: SelectObject, props: {} }],
	'attack-paths': [{ component: SelectObject, props: {} }],
	'operational-scenarios': [{ component: SelectObject, props: {} }]
};

export function getListViewFields({
	key,
	featureFlags = {}
}: {
	key: string;
	featureFlags: Record<string, boolean>;
}) {
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
}

export const baseListViewFields = {
	folders: {
		body: [
			'name',
			'description',
			'content_type',
			'parent_folder',
			'create_iam_groups',
			'filtering_labels'
		],
		filters: ['content_type', 'filtering_labels']
	},
	perimeters: {
		body: ['ref_id', 'name', 'description', 'default_assignee', 'folder'],
		filters: ['folder', 'lc_status']
	},
	'filtering-labels': {
		body: ['label']
	},
	'risk-matrices': {
		body: ['name', 'description', 'provider', 'folder', 'is_enabled'],
		filters: ['folder', 'provider', 'is_enabled']
	},
	vulnerabilities: {
		body: [
			'ref_id',
			'name',
			'status',
			'severity',
			'state',
			'due_date',
			'applied_controls',
			'folder',
			'filtering_labels'
		],
		filters: [
			'folder',
			'filtering_labels',
			'status',
			'severity',
			'assets',
			'security_advisories',
			'cwes'
		]
	},
	'risk-assessments': {
		body: [
			'ref_id',
			'str',
			'risk_matrix',
			'status',
			'risk_scenarios_count',
			'folder',
			'perimeter',
			'updated_at'
		],
		filters: ['folder', 'perimeter', 'status']
	},
	threats: {
		body: ['ref_id', 'name', 'description', 'library', 'folder', 'filtering_labels'],
		filters: ['folder', 'provider', 'library', 'filtering_labels']
	},
	'security-advisories': {
		body: [
			'ref_id',
			'name',
			'source',
			'description',
			'cvss_base_score',
			'epss_score',
			'is_actively_exploited',
			'published_date',
			'folder',
			'filtering_labels'
		],
		filters: ['folder', 'source', 'filtering_labels']
	},
	cwes: {
		body: ['ref_id', 'name', 'description', 'library', 'folder', 'filtering_labels'],
		filters: ['folder', 'filtering_labels']
	},
	'risk-scenarios': {
		body: [
			'ref_id',
			'threats',
			'name',
			'owner',
			'inherent_level',
			'existing_applied_controls',
			'current_level',
			'within_tolerance',
			'applied_controls',
			'residual_level',
			'treatment',
			'risk_assessment'
		],
		filters: [
			'folder',
			'perimeter',
			'treatment',
			'risk_assessment',
			'owner',
			'threats',
			'assets',
			'current_level',
			'residual_level',
			'within_tolerance',
			'qualifications',
			'filtering_labels'
		]
	},
	'risk-acceptances': {
		body: ['name', 'description', 'risk_scenarios', 'state'],
		filters: ['folder', 'state', 'approver']
	},
	'validation-flows': {
		body: [
			'ref_id',
			'status',
			'created_at',
			'requester',
			'validation_deadline',
			'approver',
			'linked_models',
			'filtering_labels',
			'folder'
		],
		filters: ['folder', 'status', 'requester', 'approver', 'linked_models', 'filtering_labels']
	},
	'applied-controls': {
		body: [
			'ref_id',
			'name',
			'assets',
			'priority',
			'status',
			'owner',
			'category',
			'csf_function',
			'eta',
			'folder',
			'owner',
			'control_impact',
			'effort',
			'linked_models',
			'filtering_labels'
		],
		filters: [
			'folder',
			'status',
			'assets',
			'category',
			'csf_function',
			'priority',
			'effort',
			'control_impact',
			'filtering_labels',
			'reference_control',
			'eta__lte',
			'is_assigned',
			'owner',
			'linked_models'
		]
	},
	policies: {
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
		filters: ['folder', 'status', 'csf_function', 'owner', 'priority']
	},
	'reference-controls': {
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
		filters: ['folder', 'category', 'provider', 'csf_function', 'filtering_labels']
	},
	assets: {
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
		filters: ['folder', 'type', 'filtering_labels', 'asset_class', 'is_business_function']
	},
	'asset-class': {
		body: ['name', 'description']
	},
	users: {
		body: [
			'email',
			'first_name',
			'last_name',
			'user_groups',
			'is_active',
			'expiry_date',
			'keep_local_login',
			'is_third_party',
			'has_mfa_enabled'
		],
		filters: ['is_active', 'is_third_party']
	},
	teams: {
		body: ['name', 'description', 'team_email']
	},
	'user-groups': {
		body: ['name']
	},
	roles: {
		body: ['name', 'description']
	},
	'role-assignments': {
		body: ['user', 'user_group', 'role', 'perimeter_folders']
	},
	frameworks: {
		body: ['name', 'description', 'provider', 'compliance_assessments', 'folder'],
		filters: ['folder', 'provider']
	},
	'compliance-assessments': {
		body: [
			'ref_id',
			'name',
			'version',
			'framework',
			'folder',
			'perimeter',
			'progress',
			'created_at',
			'updated_at'
		],
		filters: ['folder', 'perimeter', 'framework', 'status']
	},
	'requirement-assessments': {
		body: ['assessable', 'name', 'description', 'compliance_assessment', 'perimeter', 'result'],
		filters: [
			'compliance_assessment',
			'requirement__assessable',
			'result',
			'compliance_assessment__perimeter'
		]
	},
	evidences: {
		body: [
			'name',
			'folder',
			'owner',
			'status',
			'updated_at',
			'filtering_labels',
			'applied_controls'
		],
		filters: ['folder', 'filtering_labels', 'status', 'owner']
	},
	'evidence-revisions': {
		body: ['version', 'evidence', 'attachment', 'size', 'updated_at'],
		filters: ['filtering_labels']
	},
	'document-revisions': {
		body: ['version_number', 'status_display', 'author', 'change_summary', 'created_at']
	},
	'managed-documents': {
		body: ['name', 'document_type', 'policy', 'locale', 'folder']
	},
	requirements: {
		body: ['ref_id', 'name', 'description', 'framework']
	},
	libraries: {
		body: ['provider', 'name', 'description', 'locales', 'objects_meta']
	},
	'stored-libraries': {
		body: [
			'provider',
			'builtin',
			'ref_id',
			'name',
			'description',
			'locales',
			'objects_meta',
			'publication_date'
		],
		filters: [
			'locale',
			'provider',
			'object_type',
			'is_loaded',
			'is_custom',
			'filtering_labels',
			'is_update'
		]
	},
	'sso-settings': {
		body: ['name', 'provider', 'provider_id']
	},
	'requirement-mapping-sets': {
		body: ['source_framework', 'target_framework'],
		filters: ['provider']
	},
	entities: {
		body: [
			'ref_id',
			'name',
			'description',
			'folder',
			'parent_entity',
			'relationship',
			'default_criticality'
		],
		filters: ['folder', 'parent_entity', 'relationship']
	},
	'entity-assessments': {
		body: [
			'name',
			'entity',
			'perimeter',
			'status',
			'due_date',
			'criticality',
			'conclusion',
			'folder'
		],
		filters: ['perimeter', 'entity', 'status', 'criticality', 'conclusion']
	},
	solutions: {
		body: ['ref_id', 'name', 'description', 'provider_entity', 'criticality', 'filtering_labels'],
		filters: ['provider_entity', 'criticality', 'filtering_labels']
	},
	contracts: {
		body: [
			'ref_id',
			'name',
			'description',
			'status',
			'start_date',
			'end_date',
			'provider_entity',
			'beneficiary_entity',
			'solutions'
		],
		filters: ['status', 'provider_entity', 'beneficiary_entity', 'solutions']
	},
	representatives: {
		body: ['email', 'entity', 'role'],
		filters: ['entity']
	},
	'business-impact-analysis': {
		body: ['name', 'perimeter', 'folder', 'status'],
		filters: ['folder', 'perimeter', 'status']
	},
	'asset-assessments': {
		body: [
			'asset_ref_id',
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
		body: ['get_human_pit', 'asset_assessment', 'quali_impact', 'qualifications', 'justification']
	},
	'dora-incident-reports': {
		body: [
			'incident',
			'incident_submission',
			'report_currency',
			'submitting_entity',
			'folder',
			'created_at'
		],
		filters: ['folder']
	},
	processings: {
		body: ['ref_id', 'name', 'description', 'status', 'nature', 'filtering_labels', 'folder'],
		filters: ['folder', 'assigned_to', 'status', 'nature', 'filtering_labels']
	},
	'right-requests': {
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
		filters: ['folder', 'owner', 'request_type', 'status', 'processings']
	},
	'data-breaches': {
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
		filters: ['folder', 'breach_type', 'risk_level', 'status', 'affected_processings']
	},
	purposes: {
		body: ['legal_basis', 'description', 'name', 'processing'],
		filters: ['processing', 'legal_basis']
	},
	'personal-data': {
		body: [
			'category',
			'is_sensitive',
			'retention',
			'deletion_policy',
			'name',
			'assets',
			'processing'
		],
		filters: ['processing', 'category', 'deletion_policy', 'is_sensitive']
	},
	'data-subjects': {
		body: ['category', 'description', 'name']
	},
	'data-recipients': {
		body: ['category', 'description', 'name']
	},
	'data-contractors': {
		body: ['entity', 'relationship_type', 'country', 'name', 'documentation_link']
	},
	'data-transfers': {
		body: ['entity', 'country', 'transfer_mechanism', 'name', 'documentation_link'],
		filters: ['transfer_mechanism']
	},
	'ebios-rm': {
		body: [
			'name',
			'description',
			'folder',
			'status',
			'quotation_method',
			'created_at',
			'updated_at'
		],
		filters: ['folder', 'category', 'origin', 'status']
	},
	'feared-events': {
		body: ['is_selected', 'ref_id', 'name', 'assets', 'description', 'qualifications', 'gravity'],
		filters: ['assets', 'qualifications', 'gravity', 'is_selected']
	},
	'ro-to': {
		body: ['is_selected', 'risk_origin', 'target_objective', 'feared_events', 'pertinence'],
		filters: ['is_selected', 'risk_origin', 'feared_events', 'pertinence']
	},
	stakeholders: {
		body: [
			'is_selected',
			'entity',
			'category',
			'current_criticality',
			'applied_controls',
			'residual_criticality'
		],
		filters: ['is_selected', 'entity', 'category']
	},
	'strategic-scenarios': {
		body: [
			'ref_id',
			'name',
			'description',
			'ro_to_couple',
			'feared_events',
			'focused_feared_event',
			'attack_paths',
			'gravity'
		],
		filters: ['gravity']
	},
	'attack-paths': {
		body: [
			'is_selected',
			'ref_id',
			'name',
			'risk_origin',
			'target_objective',
			'stakeholders',
			'description'
		],
		filters: ['is_selected', 'stakeholders']
	},
	'operational-scenarios': {
		body: [
			'is_selected',
			'strategic_scenario',
			'attack_path',
			'operating_modes',
			'operating_modes_description',
			'likelihood'
		],
		filters: ['threats', 'likelihood', 'is_selected']
	},
	'elementary-actions': {
		body: ['ref_id', 'folder', 'icon_fa_class', 'name', 'attack_stage', 'threat'],
		filters: ['attack_stage']
	},
	'operating-modes': {
		body: ['ref_id', 'name', 'likelihood']
	},
	'kill-chains': {
		body: ['elementary_action', 'attack_stage', 'antecedents', 'logic_operator']
	},
	'security-exceptions': {
		body: [
			'ref_id',
			'name',
			'severity',
			'status',
			'expiration_date',
			'folder',
			'associated_objects_count',
			'created_at'
		],
		filters: ['folder', 'severity', 'status']
	},
	'findings-assessments': {
		body: [
			'ref_id',
			'name',
			'category',
			'evidences',
			'findings_count',
			'treatment_progress',
			'folder',
			'perimeter'
		],
		filters: ['folder', 'perimeter', 'category']
	},
	findings: {
		body: [
			'ref_id',
			'name',
			'description',
			'findings_assessment',
			'severity',
			'priority',
			'owner',
			'status',
			'applied_controls',
			'filtering_labels'
		],
		filters: ['filtering_labels', 'severity', 'status', 'priority', 'owner']
	},
	incidents: {
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
		filters: [
			'folder',
			'qualifications',
			'entities',
			'status',
			'detection',
			'severity',
			'filtering_labels'
		]
	},
	'timeline-entries': {
		body: ['entry_type', 'entry', 'author', 'created_at', 'updated_at', 'timestamp']
	},
	campaigns: {
		body: ['name', 'description', 'frameworks', 'status'],
		filters: ['status', 'frameworks']
	},
	'organisation-objectives': {
		body: [
			'ref_id',
			'name',
			'folder',
			'status',
			'health',
			'is_active',
			'start_date',
			'eta',
			'due_date',
			'closing_date',
			'assigned_to'
		],
		filters: ['folder', 'status', 'health', 'is_active']
	},
	'organisation-issues': {
		body: [
			'ref_id',
			'name',
			'category',
			'origin',
			'status',
			'start_date',
			'expiration_date',
			'folder'
		],
		filters: ['folder', 'category', 'origin', 'status']
	},
	'quantitative-risk-studies': {
		body: ['name', 'description', 'status', 'updated_at', 'folder'],
		filters: ['folder', 'status']
	},
	'quantitative-risk-scenarios': {
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
		filters: ['status', 'assets', 'threats', 'is_selected']
	},
	'quantitative-risk-hypotheses': {
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
		filters: ['is_selected', 'risk_stage']
	},
	'task-templates': {
		body: [
			'ref_id',
			'name',
			'is_recurrent',
			'assigned_to',
			'task_date',
			'last_occurrence_status',
			'next_occurrence',
			'next_occurrence_status',
			'folder',
			'filtering_labels'
		],
		filters: [
			'folder',
			'assigned_to',
			'is_recurrent',
			'last_occurrence_status',
			'next_occurrence_status',
			'filtering_labels'
		]
	},
	'task-nodes': {
		body: ['due_date', 'status'],
		filters: ['status', 'past']
	},
	qualifications: {
		body: ['name', 'abbreviation']
	},
	terminologies: {
		body: ['field_path', 'name', 'description', 'translations', 'is_visible'],
		filters: ['field_path', 'builtin', 'is_visible']
	},
	'generic-collections': {
		body: ['ref_id', 'name', 'description', 'filtering_labels', 'folder'],
		filters: ['folder', 'filtering_labels']
	},
	accreditations: {
		body: ['ref_id', 'name', 'category', 'status', 'authority', 'author', 'expiry_date', 'folder'],
		filters: ['folder', 'status', 'category', 'authority', 'filtering_labels']
	},
	projects: {
		body: ['kind', 'ref_id', 'name', 'status', 'health', 'owner', 'progress', 'folder'],
		filters: ['folder', 'kind', 'status', 'health', 'filtering_labels']
	},
	'responsibility-matrices': {
		body: ['ref_id', 'name', 'preset', 'activities_count', 'folder'],
		filters: ['folder', 'filtering_labels']
	},
	'responsibility-roles': {
		body: ['code', 'name', 'taxonomy', 'color', 'order', 'builtin'],
		filters: []
	},
	'responsibility-matrix-activities': {
		body: ['name', 'description', 'order', 'matrix'],
		filters: []
	},
	'responsibility-assignments': {
		body: ['activity', 'actor', 'role'],
		filters: []
	},
	'metric-definitions': {
		body: [
			'ref_id',
			'name',
			'description',
			'category',
			'unit',
			'provider',
			'filtering_labels',
			'folder'
		],
		filters: ['folder', 'category', 'library', 'provider', 'filtering_labels']
	},
	'metric-instances': {
		body: [
			'ref_id',
			'name',
			'metric_definition',
			'raw_value',
			'target_value',
			'unit',
			'status',
			'last_refresh',
			'folder'
		],
		filters: ['folder', 'metric_definition', 'status', 'owner', 'filtering_labels']
	},
	'custom-metric-samples': {
		body: ['metric_instance', 'timestamp', 'display_value']
	},
	dashboards: {
		body: ['ref_id', 'name', 'description', 'widget_count', 'filtering_labels', 'folder'],
		filters: ['folder', 'filtering_labels']
	},
	'dashboard-widgets': {
		body: [
			'display_title',
			'metric_instance',
			'chart_type_display',
			'time_range_display',
			'dashboard'
		],
		filters: ['folder', 'dashboard', 'metric_instance', 'chart_type']
	},
	'dashboard-text-widgets': {
		body: ['display_title', 'dashboard'],
		filters: ['folder', 'dashboard']
	},
	'dashboard-builtin-widgets': {
		body: ['display_title', 'dashboard'],
		filters: ['folder', 'dashboard']
	},
	actors: {
		body: ['specific', 'type']
	},
	extra: {
		body: ['users'],
		filters: ['risk', 'probability', 'impact', 'likelihood', 'gravity']
	},
	journeys: {
		body: ['name', 'preset', 'folder', 'applied_version', 'applied_at', 'applied_by'],
		filters: ['folder']
	}
} as const;

export type BaseListViewFields = typeof baseListViewFields;

// Mirrors the lightweight filter keys into the extension type so "table.ts" must provide matching filter entries and cannot add filters to models without them.
type BaseFilterExtension<K extends keyof BaseListViewFields> = BaseListViewFields[K] extends {
	filters: readonly (infer FilterKey)[];
}
	? { filters: { [F in FilterKey & string]: unknown } }
	: { filters?: never };

// UI-side extension authored in "table.ts".
// `body` is forbidden so the base config remains the only source of truth for field bodies.
export type ListViewFieldExtensions = {
	[K in keyof BaseListViewFields]: Record<string, unknown> & {
		body?: never;
	} & BaseFilterExtension<K>;
};

// Final merged type returned by defineListViewFields, with a default empty `head` when an extension does not provide one.
type DefinedListViewFields<T extends ListViewFieldExtensions> = {
	-readonly [K in keyof BaseListViewFields]: Omit<BaseListViewFields[K], 'filters'> &
		T[K] & {
			head: T[K] extends { head: infer Head } ? Head : readonly [];
		};
};

export function defineListViewFields<const T extends ListViewFieldExtensions>(extensions: T) {
	const merged = {} as DefinedListViewFields<T>;

	for (const key of Object.keys(baseListViewFields) as Array<keyof BaseListViewFields>) {
		merged[key] = {
			head: [],
			...baseListViewFields[key],
			...extensions[key]
		} as DefinedListViewFields<T>[typeof key];
	}

	return merged;
}

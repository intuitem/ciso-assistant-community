import type { z } from 'zod';
import type { ModelMapEntry } from './crud';
import type { RiskScenarioSchema } from './schemas';

export interface User {
	id: string;
	actor_id: string;
	all_actor_ids: string[];
	email: string;
	first_name: string;
	last_name: string;
	is_active: boolean;
	keep_local_login: boolean;
	date_joined: string;
	user_groups: Record<string, any>[];
	roles: Record<string, any>[];
	permissions: Record<string, any>[];
	is_third_party: boolean;
	is_admin: boolean;
	accessible_domains: string[];
	domain_permissions: Record<string, string[]>;
	root_folder_id: string;
	preferences: {
		lang?: string;
	};
}

export interface GlobalSettings {
	name: string;
	settings: Record<string, any>;
}

export interface LoginRequestBody {
	email: string;
	password: string;
}

export const URL_MODEL = [
	'folders',
	'perimeters',
	'risk-matrices',
	'risk-assessments',
	'threats',
	'risk-scenarios',
	'applied-controls',
	'policies',
	'risk-acceptances',
	'validation-flows',
	'reference-controls',
	'assets',
	'actors',
	'teams',
	'users',
	'user-groups',
	'roles',
	'role-assignments',
	'compliance-assessments',
	'evidences',
	'evidence-revisions',
	'frameworks',
	'requirements',
	'requirement-assessments',
	'stored-libraries',
	'loaded-libraries',
	'libraries',
	'sso-settings',
	'general-settings',
	'feature-flags',
	'requirement-mapping-sets',
	'entities',
	'entity-assessments',
	'solutions',
	'contracts',
	'representatives',
	'vulnerabilities',
	'filtering-labels',
	'library-filtering-labels',
	// 'ebios-rm',
	'feared-events',
	'ro-to',
	'stakeholders',
	'strategic-scenarios',
	'attack-paths',
	'operational-scenarios',
	'elementary-actions',
	'operating-modes',
	'kill-chains',
	'processings',
	'processing-natures',
	'security-exceptions',
	'findings',
	'findings-assessments',
	// privacy,
	'processings',
	'right-requests',
	'data-breaches',
	'purposes',
	'personal-data',
	'data-subjects',
	'data-recipients',
	'data-contractors',
	'data-transfers',
	// incidents,
	'incidents',
	'timeline-entries',
	// tasks,
	'task-templates',
	'task-nodes',
	// resilience,
	'business-impact-analysis',
	'escalation-thresholds',
	'asset-assessments',
	'asset-class',
	'asset-capabilities',
	// campaigns,
	'campaigns',
	// iso,
	'organisation-issues',
	'organisation-objectives',
	// crq,
	'quantitative-risk-studies',
	'quantitative-risk-scenarios',
	'quantitative-risk-hypotheses',
	// terminologies
	'terminologies',
	// roles,
	'roles',
	'permissions',
	// pmbok
	'generic-collections',
	'accreditations',
	// metrology
	'metric-definitions',
	'metric-instances',
	'custom-metric-samples',
	'dashboards',
	'dashboard-widgets',
	'dashboard-text-widgets',
	'dashboard-builtin-widgets',
	// rmf operations
	'stig-checklists',
	'stig-findings',
	'vulnerability-findings',
	'checklist-scores',
	'system-groups',
	'nessus-scans',
	'scap-results',
	// oscal integration
	'oscal-documents',
	'oscal-catalogs',
	'oscal-profiles',
	'oscal-ssps',
	'oscal-components',
	// poam
	'poam-items',
	'poam-milestones',
	// questionnaires enhanced
	'questionnaire-modules'
] as const;

export const THIRD_PARTY_URL_MODEL = [
	'compliance-assessments',
	'evidences',
	'evidence-revisions'
] as const;

export type urlModel = (typeof URL_MODEL)[number];

export type thirdPartyUrlModel = (typeof THIRD_PARTY_URL_MODEL)[number];

export type ModelInfo = ModelMapEntry;

interface ProbabilityImpactItem {
	abbreviation: string;
	name: string;
	description: string;
}

interface RiskItem extends ProbabilityImpactItem {
	hexcolor: string;
}

export interface RiskMatrixJsonDefinition {
	name: string;
	description: string;
	probability: ProbabilityImpactItem[];
	impact: ProbabilityImpactItem[];
	risk: RiskItem[];
	grid: number[][];
}

export interface RiskMatrix {
	locale?: string; // optional, defaults en english.
	name: string;
	description: string;
	format_version?: string;
	json_definition: string; // stringified
}

export interface Perimeter {
	id: string;
	folder: Record<string, any>;
	lc_status: string;
	created_at: string;
	updated_at: string;
	is_published: boolean;
	name: string;
	description?: string;
	ref_id?: string;
	compliance_assessments: Record<string, any>[];
}

export type RiskScenario = z.infer<typeof RiskScenarioSchema>;

interface LibraryObject {
	type: 'risk_matrix' | 'reference_control' | 'threat';
	fields: Record<string, any>;
}

export interface Library {
	name: string;
	urn: string;
	id?: string;
	dependencies: string[];
	description: string;
	locale: 'en' | 'fr';
	format_version: string;
	objects: LibraryObject[];
	copyright: string;
	provider: string;
	packager: string;
}

export interface RiskLevel {
	current: string[];
	residual: string[];
}

export interface StrengthOfKnowledgeEntry {
	name: string;
	description: string;
	symbol: string;
}

export interface AggregatedData {
	names: string[];
}

export interface AppliedControlStatus {
	localLables: string[];
	labels: any[];
	values: any[]; // Set these types later on
}

export interface AppliedControlImpact {
	localLables: string[];
	labels: any[];
	values: any[]; // Set these types later on
}

export interface CacheLock {
	promise: Promise<any>;
	resolve: (_: any) => any;
}

// ============================================================================
// OSCAL Integration Types (matches backend/oscal_integration/services/)
// ============================================================================

/** OSCAL document formats */
export type OscalFormat = 'json' | 'yaml' | 'xml';

/** OSCAL model types */
export type OscalModelType =
	| 'catalog'
	| 'profile'
	| 'component-definition'
	| 'ssp'
	| 'assessment-plan'
	| 'assessment-results'
	| 'poam';

/** Result of splitting an OSCAL document (matches trestle_service.SplitResult) */
export interface OscalSplitResult {
	success: boolean;
	original_path: string;
	split_paths: string[];
	model_type: string;
	split_count: number;
	errors: string[];
}

/** Result of merging OSCAL documents (matches trestle_service.MergeResult) */
export interface OscalMergeResult {
	success: boolean;
	merged_path: string;
	source_paths: string[];
	model_type: string;
	errors: string[];
}

/** Result of profile resolution (matches trestle_service.ProfileResolutionResult) */
export interface OscalProfileResolutionResult {
	success: boolean;
	resolved_catalog: Record<string, any>;
	source_profile: string;
	imported_catalogs: string[];
	control_count: number;
	errors: string[];
}

/** OSCAL validation result (matches trestle_service.ValidationResult) */
export interface OscalValidationResult {
	valid: boolean;
	model_type: string | null;
	oscal_version: string;
	errors: Array<{ path: string; message: string }>;
	warnings: Array<{ path: string; message: string }>;
	duplicate_ids: string[];
	missing_references: string[];
}

/** OSCAL document structure for editor */
export interface OscalDocument {
	type: OscalModelType;
	content: Record<string, any>;
	metadata?: OscalMetadata;
}

export interface OscalMetadata {
	title: string;
	'last-modified': string;
	version: string;
	'oscal-version': string;
}

export interface OscalControl {
	id: string;
	title: string;
	class?: string;
	props?: OscalProperty[];
	parts?: OscalPart[];
	params?: OscalParameter[];
}

export interface OscalProperty {
	name: string;
	value: string;
	ns?: string;
}

export interface OscalPart {
	id?: string;
	name: string;
	prose?: string;
	parts?: OscalPart[];
}

export interface OscalParameter {
	id: string;
	label?: string;
	guidelines?: { prose: string }[];
	values?: string[];
	select?: { 'how-many'?: string; choice: string[] };
}

// ============================================================================
// FedRAMP Types (matches backend/oscal_integration/services/fedramp_enhanced.py)
// ============================================================================

/** FedRAMP control origination types */
export type ControlOrigination =
	| 'sp-corporate'
	| 'sp-system'
	| 'customer-configured'
	| 'customer-provided'
	| 'inherited'
	| 'shared'
	| 'hybrid';

/** FedRAMP implementation status */
export type FedRAMPImplementationStatus =
	| 'implemented'
	| 'partially-implemented'
	| 'planned'
	| 'alternative-implementation'
	| 'not-applicable';

/** FedRAMP baselines */
export type FedRAMPBaseline = 'LOW' | 'MODERATE' | 'HIGH' | 'LI_SAAS';

/** Control origination info (matches fedramp_enhanced.ControlOriginationInfo) */
export interface ControlOriginationInfo {
	control_id: string;
	originations: ControlOrigination[];
	description: string;
	responsible_roles: string[];
	implementation_status: FedRAMPImplementationStatus;
}

/** FedRAMP responsible role (matches fedramp_enhanced.ResponsibleRole) */
export interface FedRAMPResponsibleRole {
	role_id: string;
	title: string;
	party_uuids: string[];
	description: string;
}

/** FedRAMP validation result (matches fedramp_enhanced.FedRAMPValidationResult) */
export interface FedRAMPValidationResult {
	valid: boolean;
	baseline: FedRAMPBaseline;
	compliance_percentage: number;
	total_controls: number;
	implemented_controls: number;
	partially_implemented: number;
	planned_controls: number;
	not_applicable: number;
	missing_controls: string[];
	origination_issues: Array<{ control_id: string; issue: string }>;
	role_issues: Array<{ role_id: string; issue: string }>;
	errors: string[];
	warnings: string[];
}

// ============================================================================
// Base Aggregate Types (matches backend/core/domain/aggregate.py)
// ============================================================================

/** Base fields for all DDD aggregates (from AggregateRoot) */
export interface AggregateBase {
	id: string; // UUID
	version: number; // Optimistic locking version
	created_at: string; // ISO datetime
	updated_at: string; // ISO datetime
	created_by: string | null; // UUID of user who created
	updated_by: string | null; // UUID of user who last updated
}

// ============================================================================
// RMF Operations Types (matches backend/core/bounded_contexts/rmf_operations/)
// ============================================================================

/** SCAP parsing result (matches rmf_enhanced.ScapResult) */
export interface ScapResult {
	benchmark_id: string;
	benchmark_title: string;
	benchmark_version: string;
	profile_id: string;
	target_id: string;
	target_hostname: string;
	start_time: string; // ISO datetime
	end_time: string; // ISO datetime
	rules: Array<{
		rule_id: string;
		result: string;
		severity: string;
		title: string;
		description: string;
	}>;
	score: number;
	pass_count: number;
	fail_count: number;
	error_count: number;
	notchecked_count: number;
}

/** Asset metadata (matches rmf_enhanced.AssetMetadata) */
export interface AssetMetadata {
	hostname: string;
	ip_addresses: string[];
	mac_addresses: string[];
	fqdn: string;
	technology_area: string;
	asset_type: string;
	role: string;
	operating_system: string;
	os_version: string;
	location: string;
	department: string;
	system_administrator: string;
	is_internet_facing: boolean;
	classification: string;
}

/** RMF document generation result (matches rmf_enhanced.RMFDocumentResult) */
export interface RMFDocumentResult {
	success: boolean;
	document_type: string;
	content: string; // base64 encoded bytes in frontend
	filename: string;
	errors: string[];
}

/** System compliance score (matches rmf_enhanced.SystemScore) */
export interface SystemScore {
	system_group_id: string;
	system_name: string;
	total_checklists: number;
	total_findings: number;
	cat1_open: number;
	cat1_closed: number;
	cat2_open: number;
	cat2_closed: number;
	cat3_open: number;
	cat3_closed: number;
	compliance_percentage: number;
	risk_score: number;
	last_calculated: string; // ISO datetime
}

/** STIG checklist status */
export type STIGFindingStatus = 'open' | 'not_a_finding' | 'not_applicable' | 'not_reviewed';

/** STIG severity category */
export type STIGSeverity = 'cat1' | 'cat2' | 'cat3';

/** STIG vulnerability finding */
export interface STIGVulnerabilityFinding {
	id: string;
	vuln_id: string;
	rule_id: string;
	stig_id: string;
	severity: STIGSeverity;
	status: STIGFindingStatus;
	finding_details: string;
	comments: string;
	cci_ids: string[];
	check_content: string;
	fix_text: string;
	rule_title: string;
	discussion: string;
	false_positives: string;
	false_negatives: string;
	documentable: boolean;
	mitigations: string;
	severity_override: string;
	severity_override_guidance: string;
	potential_impacts: string;
	third_party_tools: string;
	ia_controls: string;
}

/** STIG checklist lifecycle state */
export type STIGChecklistLifecycleState = 'draft' | 'active' | 'archived';

/** STIG checklist asset type */
export type STIGChecklistAssetType =
	| 'computing'
	| 'network'
	| 'storage'
	| 'application'
	| 'database'
	| 'web_server'
	| 'other';

/** STIG checklist (matches aggregates/stig_checklist.py) */
export interface STIGChecklist extends AggregateBase {
	// Identity and system relationship
	systemGroupId: string | null; // UUID
	hostName: string;

	// STIG metadata
	stigType: string;
	stigRelease: string;
	// version is inherited from name field in some contexts

	// Lifecycle
	lifecycle_state: STIGChecklistLifecycleState;

	// Asset information (extracted from CKL file)
	assetInfo: Record<string, any>;

	// Raw CKL data for export/re-import
	rawCklData: Record<string, any>;

	// Web/Database specific fields (OpenRMF naming convention)
	isWebDatabase: boolean;
	webDatabaseSite: string;
	webDatabaseInstance: string;

	// Asset type classification
	asset_type: STIGChecklistAssetType;

	// Relationships
	vulnerabilityFindingIds: string[]; // UUID array

	// Metadata
	tags: string[];

	// Convenience fields for display (may be computed)
	name?: string;
	stig_id?: string;
	stig_version?: string;
	release_info?: string;
	classification?: string;
	asset?: AssetMetadata;
	findings?: STIGVulnerabilityFinding[];
}

/** System group lifecycle state */
export type SystemGroupLifecycleState = 'draft' | 'active' | 'archived';

/** System group (matches aggregates/system_group.py) */
export interface SystemGroup extends AggregateBase {
	// Identity and core fields
	name: string;
	description: string | null;

	// Lifecycle
	lifecycle_state: SystemGroupLifecycleState;

	// Embedded ID arrays for relationships
	checklistIds: string[]; // UUID array
	assetIds: string[]; // UUID array
	nessusScanIds: string[]; // UUID array

	// Asset hierarchy and relationships
	asset_hierarchy: Record<string, any>;

	// Compliance tracking
	last_compliance_check: string | null; // ISO datetime

	// Metadata
	tags: string[];

	// Computed fields (updated by projection handlers)
	totalChecklists: number;
	totalOpenVulnerabilities: number;
	totalCat1Open: number;
	totalCat2Open: number;
	totalCat3Open: number;
}

/** Checklist score (matches aggregates/checklist_score.py) */
export interface ChecklistScore extends AggregateBase {
	// Identity
	checklistId: string; // UUID
	systemGroupId: string | null; // UUID

	// Host information (denormalized for queries)
	hostName: string;
	stigType: string;

	// Category 1 (High/CAT I) counts
	totalCat1Open: number;
	totalCat1NotAFinding: number;
	totalCat1NotApplicable: number;
	totalCat1NotReviewed: number;

	// Category 2 (Medium/CAT II) counts
	totalCat2Open: number;
	totalCat2NotAFinding: number;
	totalCat2NotApplicable: number;
	totalCat2NotReviewed: number;

	// Category 3 (Low/CAT III) counts
	totalCat3Open: number;
	totalCat3NotAFinding: number;
	totalCat3NotApplicable: number;
	totalCat3NotReviewed: number;

	// Metadata
	lastCalculatedAt: string; // ISO datetime

	// Computed properties (frontend convenience)
	checklist_id?: string;
	checklist_name?: string;
	cat1_open?: number;
	cat1_closed?: number;
	cat2_open?: number;
	cat2_closed?: number;
	cat3_open?: number;
	cat3_closed?: number;
	total_open?: number;
	total_closed?: number;
	compliance_percentage?: number;
	last_updated?: string;
}

/** Nessus scan processing status */
export type NessusScanProcessingStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

/** Nessus scan (matches aggregates/nessus_scan.py) */
export interface NessusScan extends AggregateBase {
	systemGroupId: string; // UUID

	// File information
	filename: string;
	raw_xml_content: string;

	// Scan metadata (extracted from XML)
	scan_date: string | null; // ISO datetime
	scanner_version: string | null;
	policy_name: string | null;

	// Statistics (computed from XML)
	total_hosts: number;
	total_vulnerabilities: number;
	scan_duration_seconds: number | null;

	// Severity breakdown
	critical_count: number;
	high_count: number;
	medium_count: number;
	low_count: number;
	info_count: number;

	// Correlation data
	correlated_checklist_ids: string[]; // UUID array

	// Additional metadata
	tags: string[];

	// Processing status
	processing_status: NessusScanProcessingStatus;
	processing_error: string | null;
}

/** Vulnerability finding (matches aggregates/vulnerability_finding.py) */
export interface VulnerabilityFinding extends AggregateBase {
	// Identity and relationships
	checklistId: string; // UUID
	vulnId: string;
	stigId: string;
	ruleId: string;

	// Vulnerability details
	ruleTitle: string;
	ruleDiscussion: string | null;
	checkContent: string | null;
	fixText: string | null;

	// Status and severity
	status_data: {
		status: STIGFindingStatus;
		finding_details: string | null;
		comments: string | null;
		severity_override: string | null;
		severity_justification: string | null;
	};
	severity_category: STIGSeverity;

	// Additional metadata
	ruleVersion: string;
	cciIds: string[];

	// Metadata
	tags: string[];
}

// ============================================================================
// Questionnaire Types (matches backend/questionnaires/services/govready_enhanced.py)
// ============================================================================

/** Condition operators for conditional logic */
export type ConditionOperator =
	| 'equals'
	| 'not_equals'
	| 'contains'
	| 'not_contains'
	| 'greater_than'
	| 'less_than'
	| 'greater_or_equal'
	| 'less_or_equal'
	| 'is_empty'
	| 'is_not_empty'
	| 'matches'
	| 'in'
	| 'not_in';

/** Condition evaluation result (matches govready_enhanced.ConditionResult) */
export interface ConditionResult {
	satisfied: boolean;
	question_id: string;
	condition: Record<string, any>;
	actual_value: any;
	expected_value: any;
}

/** Question visibility result (matches govready_enhanced.QuestionVisibility) */
export interface QuestionVisibility {
	question_id: string;
	visible: boolean;
	reason: string;
	imputed_value: any | null;
}

/** Module specification (matches govready_enhanced.ModuleSpec) */
export interface ModuleSpec {
	module_id: string;
	title: string;
	description: string;
	version: string;
	questions: Array<{
		id: string;
		prompt: string;
		type: string;
		choices?: string[];
		conditional_logic?: Record<string, any>;
	}>;
	output_documents: Array<{
		id: string;
		title: string;
		template: string;
	}>;
	control_mappings: Record<string, string[]>; // question_id -> control_ids
	metadata: Record<string, any>;
}

/** Generated control statement (matches govready_enhanced.GeneratedStatement) */
export interface GeneratedStatement {
	control_id: string;
	statement_text: string;
	source_questions: string[];
	confidence: number; // 0.0 - 1.0
	parameters: Record<string, any>;
}

// ============================================================================
// POA&M Types (matches backend/poam/services/poam_export.py)
// ============================================================================

/** POA&M deviation types */
export type POAMDeviationType = 'OR' | 'FR' | 'FP' | 'VENDOR_DEPENDENCY';

/** Export result (matches poam_export.ExportResult) */
export interface POAMExportResult {
	success: boolean;
	content: string; // base64 encoded bytes
	filename: string;
	content_type: string;
	errors: string[];
}

/** POA&M milestone */
export interface POAMMilestone {
	id: string;
	description: string;
	due_date: string;
	completion_date: string | null;
	status: 'open' | 'completed' | 'in_progress';
}

/** POA&M item */
export interface POAMItem {
	id: string;
	poam_id: string;
	weakness_name: string;
	weakness_description: string;
	detector_source: string;
	source_id: string;
	asset_identifier: string;
	point_of_contact: string;
	resources_required: string;
	scheduled_completion_date: string;
	milestones: POAMMilestone[];
	milestone_changes: string;
	status: 'open' | 'completed' | 'in_progress' | 'delayed';
	comments: string;
	control_id: string;
	original_risk_rating: 'HIGH' | 'MODERATE' | 'LOW';
	adjusted_risk_rating: 'HIGH' | 'MODERATE' | 'LOW';
	risk_adjustment: string;
	false_positive: boolean;
	operational_requirement: boolean;
	deviation_type: POAMDeviationType | null;
	deviation_rationale: string;
	vendor_dependency: boolean;
	vendor_product_name: string;
	vendor_checkin_date: string | null;
	supporting_documents: string[];
	auto_approve: boolean;
	completion_date: string | null;
	created_at: string;
	updated_at: string;
}

// ============================================================================
// OpenControl Types (matches backend/oscal_integration/services/opencontrol_converter.py)
// ============================================================================

/** OpenControl conversion result */
export interface OpenControlConversionResult {
	success: boolean;
	content: string;
	errors: string[];
	warnings: string[];
}

/** OpenControl component structure */
export interface OpenControlComponent {
	name: string;
	key: string;
	schema_version: string;
	satisfies: Array<{
		standard_key: string;
		control_key: string;
		narrative: Array<{ key: string; text: string }>;
		implementation_status: string;
	}>;
	references: Array<{ name: string; path: string }>;
}

/** OpenControl standard structure */
export interface OpenControlStandard {
	name: string;
	controls: Record<
		string,
		{
			name: string;
			description: string;
			family?: string;
		}
	>;
}

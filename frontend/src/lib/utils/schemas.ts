// schema for the validation of forms
import { z, type AnyZodObject } from 'zod';
import * as m from '$paraglide/messages';

const toArrayPreprocessor = (value: unknown) => {
	if (Array.isArray(value)) {
		return value;
	}

	switch (typeof value) {
		case 'string':
		case 'number':
		case 'bigint':
		case 'boolean':
			return [value];

		default:
			return value; // could not coerce, return the original and face the consequences during validation
	}
};

// JSON schema
const literalSchema = z.union([z.string(), z.number(), z.boolean(), z.null()]);
type Literal = z.infer<typeof literalSchema>;
type Json = Literal | { [key: string]: Json } | Json[];
const jsonSchema: z.ZodType<Json> = z.lazy(() =>
	z.union([literalSchema, z.array(jsonSchema), z.record(jsonSchema)])
);

export const quickStartSchema = z.object({
	folder: z.string().uuid().optional(),
	audit_name: z.string().nonempty(),
	framework: z.string().url(),
	create_risk_assessment: z.boolean().default(true),
	risk_matrix: z.string().url().optional(),
	risk_assessment_name: z.string().optional()
});

export const loginSchema = z
	.object({
		username: z
			.string({
				required_error: 'Email is required'
			})
			.email(),
		password: z.string({
			required_error: 'Password is required'
		})
	})
	.required();

export const emailSchema = z
	.object({
		email: z.string({
			required_error: 'Email is required'
		})
	})
	.required();

// Utility functions for commonly used schema structures
const nameSchema = z
	.string({
		required_error: 'Name is required'
	})
	.min(1);

const descriptionSchema = z.string().optional().nullable();

const NameDescriptionMixin = {
	name: nameSchema,
	description: descriptionSchema
};

export const FolderSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional(),
	parent_folder: z.string().optional()
});

export const FolderImportSchema = z.object({
	name: nameSchema,
	file: z.instanceof(File),
	load_missing_libraries: z.coerce.boolean().default(false)
	//NOTE: coerce is used to handle checkbox form values which can be strings ('true'/'false')
	//or booleans (true/false). Without coerce, form validation fails inconsistently.
});

export const PerimeterSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	lc_status: z.string().optional().default('in_design')
});

export const RiskMatrixSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	json_definition: z.string(),
	is_enabled: z.boolean()
});

export const LibraryUploadSchema = z.object({
	file: z.instanceof(File).optional()
});

export const RiskAssessmentSchema = z.object({
	...NameDescriptionMixin,
	version: z.string().optional().default('0.1'),
	perimeter: z.string(),
	status: z.string().optional().nullable(),
	ref_id: z.string().optional(),
	risk_matrix: z.string(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	observation: z.string().optional().nullable(),
	ebios_rm_study: z.string().uuid().optional()
});

export const ThreatSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	provider: z.string().optional().nullable(),
	ref_id: z.string().optional(),
	annotation: z.string().optional().nullable(),
	filtering_labels: z.string().optional().array().optional()
});

export const RiskScenarioSchema = z.object({
	...NameDescriptionMixin,
	applied_controls: z.string().uuid().optional().array().optional(),
	existing_applied_controls: z.string().uuid().optional().array().optional(),
	current_proba: z.number().optional(),
	current_impact: z.number().optional(),
	residual_proba: z.number().optional(),
	residual_impact: z.number().optional(),
	treatment: z.string().optional(),
	qualifications: z.string().optional().array().optional(),
	strength_of_knowledge: z.number().default(-1).optional(),
	justification: z.string().optional().nullable(),
	risk_assessment: z.string(),
	threats: z.string().uuid().optional().array().optional(),
	assets: z.string().uuid().optional().array().optional(),
	vulnerabilities: z.string().uuid().optional().array().optional(),
	owner: z.string().uuid().optional().array().optional(),
	security_exceptions: z.string().uuid().optional().array().optional(),
	ref_id: z.string().max(100).optional()
});

export const AppliedControlSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional(),
	category: z.string().optional().nullable(),
	csf_function: z.string().optional().nullable(),
	priority: z.number().optional().nullable(),
	status: z.string().optional().default('--'),
	evidences: z.string().optional().array().optional(),
	assets: z.string().optional().array().optional(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	start_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	expiry_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	link: z.string().url().optional().or(z.literal('')),
	effort: z.string().optional().nullable(),
	control_impact: z.number().optional().nullable(),
	cost: z.number().multipleOf(0.000001).optional().nullable(),
	folder: z.string(),
	reference_control: z.string().optional().nullable(),
	owner: z.string().uuid().optional().array().optional(),
	security_exceptions: z.string().uuid().optional().array().optional(),
	progress_field: z.number().optional().default(0),
	filtering_labels: z.string().optional().array().optional(),
	findings: z.string().uuid().optional().array().optional()
});

export const AppliedControlDuplicateSchema = z.object({
	...AppliedControlSchema.shape,
	duplicate_evidences: z.boolean()
});

export const PolicySchema = AppliedControlSchema.omit({ category: true });

export const RiskAcceptanceSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	expiry_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	justification: z.string().optional().nullable(),
	approver: z.string().optional().nullable(),
	risk_scenarios: z.array(z.string())
});

export const ReferenceControlSchema = z.object({
	...NameDescriptionMixin,
	provider: z.string().optional().nullable(),
	category: z.string().optional().nullable(),
	csf_function: z.string().optional().nullable(),
	folder: z.string(),
	ref_id: z.string().optional(),
	annotation: z.string().optional().nullable(),
	filtering_labels: z.string().optional().array().optional()
});

export const AssetSchema = z.object({
	...NameDescriptionMixin,
	type: z.string().default('PR'),
	folder: z.string(),
	parent_assets: z.string().optional().array().optional(),
	security_objectives: z
		.object({
			objectives: z
				.record(
					z.string(),
					z.object({
						value: z.number().nonnegative().optional(),
						is_enabled: z.boolean().default(false)
					})
				)
				.optional()
		})
		.optional(),
	disaster_recovery_objectives: z
		.object({
			objectives: z
				.record(
					z.string(),
					z.object({
						value: z.number().nonnegative().optional()
					})
				)
				.optional()
		})
		.optional(),
	reference_link: z.string().url().optional().or(z.literal('')),
	owner: z.string().uuid().optional().array().optional(),
	filtering_labels: z.string().optional().array().optional(),
	ebios_rm_studies: z.string().uuid().optional().array().optional(),
	security_exceptions: z.string().uuid().optional().array().optional(),
	ref_id: z.string().max(100).optional()
});

export const FilteringLabelSchema = z.object({
	label: z.string()
});

export const RequirementAssessmentSchema = z.object({
	answers: jsonSchema,
	status: z.string(),
	result: z.string(),
	is_scored: z.boolean().optional(),
	score: z.number().optional().nullable(),
	documentation_score: z.number().optional().nullable(),
	comment: z.string().optional().nullable(),
	folder: z.string(),
	requirement: z.string(),
	evidences: z.array(z.string().uuid().optional()).optional(),
	compliance_assessment: z.string(),
	applied_controls: z.array(z.string().uuid().optional()).optional(),
	observation: z.string().optional().nullable(),
	security_exceptions: z.string().uuid().optional().array().optional()
});

export const UserEditSchema = z.object({
	email: z.string().email(),
	first_name: z.string().optional(),
	last_name: z.string().optional(),
	is_active: z.boolean().optional(),
	user_groups: z.array(z.string().uuid().optional()).optional()
});

export const UserCreateSchema = z.object({ email: z.string().email() });
export const ChangePasswordSchema = z.object({
	old_password: z.string(),
	new_password: z.string(),
	confirm_new_password: z.string()
});

export const ResetPasswordSchema = z.object({
	new_password: z.string(),
	confirm_new_password: z.string()
});

export const SetPasswordSchema = z.object({
	user: z.string(),
	new_password: z.string(),
	confirm_new_password: z.string()
});

export const ComplianceAssessmentSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional(),
	perimeter: z.string(),
	status: z.string().optional().nullable(),
	selected_implementation_groups: z.array(z.string().optional()).optional(),
	framework: z.string(),
	show_documentation_score: z.boolean().optional().default(false),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	baseline: z.string().optional().nullable(),
	create_applied_controls_from_suggestions: z.boolean().optional().default(false),
	observation: z.string().optional().nullable(),
	ebios_rm_studies: z.string().uuid().optional().array().optional(),
	assets: z.string().uuid().optional().array().optional()
});

export const EvidenceSchema = z.object({
	...NameDescriptionMixin,
	attachment: z.any().optional().nullable(),
	folder: z.string(),
	applied_controls: z.preprocess(toArrayPreprocessor, z.array(z.string().optional())).optional(),
	requirement_assessments: z.string().optional().array().optional(),
	link: z.string().optional().nullable(),
	filtering_labels: z.string().optional().array().optional()
});

export const GeneralSettingsSchema = z.object({
	security_objective_scale: z.string(),
	ebios_radar_max: z.number(),
	ebios_radar_green_zone_radius: z.number(),
	ebios_radar_yellow_zone_radius: z.number(),
	ebios_radar_red_zone_radius: z.number(),
	notifications_enable_mailing: z.boolean().optional(),
	interface_agg_scenario_matrix: z.boolean().optional()
});

export const SSOSettingsSchema = z.object({
	is_enabled: z.boolean().optional(),
	provider: z.string().default('saml'),
	provider_id: z.string().optional(),
	provider_name: z.string(),
	client_id: z.string(),
	secret: z.string().optional(),
	key: z.string().optional(),

	// SAML specific fields
	attribute_mapping_uid: z
		.preprocess(toArrayPreprocessor, z.array(z.string().optional()))
		.optional(),
	attribute_mapping_email_verified: z
		.preprocess(toArrayPreprocessor, z.array(z.string().optional()))
		.optional(),
	attribute_mapping_email: z
		.preprocess(toArrayPreprocessor, z.array(z.string().optional()))
		.optional(),
	idp_entity_id: z.string().optional(),
	metadata_url: z.string().optional(),
	sso_url: z.string().optional().nullable(),
	slo_url: z.string().optional().nullable(),
	x509cert: z.string().optional(),
	sp_entity_id: z.string().optional(),
	allow_repeat_attribute_name: z.boolean().optional().nullable(),
	allow_single_label_domains: z.boolean().optional().nullable(),
	authn_request_signed: z.boolean().optional().nullable(),
	digest_algorithm: z.string().optional().nullable(),
	logout_request_signed: z.boolean().optional().nullable(),
	logout_response_signed: z.boolean().optional().nullable(),
	metadata_signed: z.boolean().optional().nullable(),
	name_id_encrypted: z.boolean().optional().nullable(),
	reject_deprecated_algorithm: z.boolean().optional().nullable(),
	reject_idp_initiated_sso: z.boolean().optional().nullable(),
	signature_algorithm: z.string().optional().nullable(),
	want_assertion_encrypted: z.boolean().optional().nullable(),
	want_assertion_signed: z.boolean().optional().nullable(),
	want_attribute_statement: z.boolean().optional().nullable(),
	want_message_signed: z.boolean().optional().nullable(),
	want_name_id: z.boolean().optional().nullable(),
	want_name_id_encrypted: z.boolean().optional().nullable()
});

export const EntitiesSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	mission: z.string().optional(),
	reference_link: z.string().url().optional().or(z.literal(''))
});

export const EntityAssessmentSchema = z.object({
	...NameDescriptionMixin,
	create_audit: z.boolean().optional().default(false),
	framework: z.string().optional(),
	selected_implementation_groups: z.array(z.string().optional()).optional(),
	version: z.string().optional().default('0.1'),
	perimeter: z.string(),
	status: z.string().optional().nullable(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	authors: z.array(z.string().optional()).optional(),
	representatives: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	entity: z.string(),
	solutions: z.array(z.string().optional()).optional(),
	compliance_assessment: z.string().optional(),
	evidence: z.string().optional(),
	criticality: z.number().optional().nullable(),
	conclusion: z.string().optional().nullable(),
	penetration: z.number().optional(),
	dependency: z.number().optional(),
	maturity: z.number().optional(),
	trust: z.number().optional(),
	observation: z.string().optional().nullable()
});

export const solutionSchema = z.object({
	...NameDescriptionMixin,
	provider_entity: z.string(),
	ref_id: z.string().optional(),
	criticality: z.number().optional(),
	assets: z.string().uuid().optional().array().optional()
});

export const representativeSchema = z.object({
	create_user: z.boolean().optional().default(false),
	email: z.string().email(),
	entity: z.string(),
	first_name: z.string().optional(),
	last_name: z.string().optional(),
	phone: z.string().optional(),
	role: z.string().optional(),
	description: z.string().optional()
});

export const vulnerabilitySchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional().default(''),
	status: z.string().default('--'),
	severity: z.number().default(-1).optional(),
	assets: z.string().uuid().optional().array().optional(),
	applied_controls: z.string().uuid().optional().array().optional(),
	security_exceptions: z.string().uuid().optional().array().optional(),
	filtering_labels: z.string().optional().array().optional()
});

export const processingSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional().default(''),
	filtering_labels: z.string().optional().array().optional(),
	status: z.string().optional(),
	legal_basis: z.string().optional(),
	dpia_required: z.boolean().optional(),
	has_sensitive_personal_data: z.boolean().optional(),
	nature: z.string().optional().array().optional()
});

export const purposeSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	processing: z.string()
});
export const dataSubjectSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	category: z.string(),
	processing: z.string()
});
export const dataRecipientSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	category: z.string(),
	processing: z.string()
});
export const dataContractorSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	relationship_type: z.string(),
	country: z.string(),
	documentation_link: z.string().optional(),
	processing: z.string(),
	entity: z.string().optional()
});
export const dataTransferSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	country: z.string(),
	documentation_link: z.string().optional(),
	legal_basis: z.string(),
	guarantees: z.string().optional(),
	processing: z.string(),
	entity: z.string().optional()
});

export const personalDataSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	category: z.string(),
	retention: z.string(),
	deletion_policy: z.string(),
	is_sensitive: z.boolean().optional(),
	processing: z.string()
});

export const ebiosRMSchema = z.object({
	...NameDescriptionMixin,
	version: z.string().optional().default('0.1'),
	ref_id: z.string().optional().default(''),
	risk_matrix: z.string(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	observation: z.string().optional().nullable(),
	assets: z.string().uuid().optional().array().optional(),
	folder: z.string(),
	compliance_assessments: z.string().uuid().optional().array().optional(),
	reference_entity: z.string().optional()
});

export const fearedEventsSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional(),
	gravity: z.number().optional().default(-1),
	is_selected: z.boolean().default(true),
	justification: z.string().optional(),
	ebios_rm_study: z.string(),
	assets: z.string().uuid().optional().array().optional(),
	qualifications: z.string().optional().array().optional()
});

export const roToSchema = z.object({
	ebios_rm_study: z.string(),
	feared_events: z.string().uuid().optional().array().optional(),
	risk_origin: z.string(),
	target_objective: z.string(),
	motivation: z.number().default(0).optional(),
	resources: z.number().default(0).optional(),
	activity: z.number().min(0).max(4).optional().default(0),
	is_selected: z.boolean().default(true),
	justification: z.string().optional()
});

export const StakeholderSchema = z.object({
	ebios_rm_study: z.string(),
	applied_controls: z.string().uuid().optional().array().optional(),
	category: z.string(),
	entity: z.string(),
	current_dependency: z.number().min(0).max(4).default(0).optional(),
	current_penetration: z.number().min(0).max(4).default(0).optional(),
	current_maturity: z.number().min(1).max(4).default(1).optional(),
	current_trust: z.number().min(1).max(4).default(1).optional(),
	current_criticality: z.number().min(0).max(16).default(0).optional(),
	residual_dependency: z.number().min(0).max(4).default(0).optional(),
	residual_penetration: z.number().min(0).max(4).default(0).optional(),
	residual_maturity: z.number().min(1).max(4).default(1).optional(),
	residual_trust: z.number().min(1).max(4).default(1).optional(),
	residual_criticality: z.number().min(0).max(16).default(0).optional(),
	is_selected: z.boolean().default(true),
	justification: z.string().optional()
});

export const StrategicScenarioSchema = z.object({
	...NameDescriptionMixin,
	ebios_rm_study: z.string(),
	ro_to_couple: z.string().uuid(),
	ref_id: z.string().optional()
});

export const AttackPathSchema = z.object({
	...NameDescriptionMixin,
	strategic_scenario: z.string().uuid(),
	stakeholders: z.string().uuid().optional().array().optional(),
	is_selected: z.boolean().default(true),
	justification: z.string().optional()
});

export const operationalScenarioSchema = z.object({
	ebios_rm_study: z.string(),
	attack_path: z.string().uuid(),
	threats: z.string().uuid().optional().array().optional(),
	operating_modes_description: z.string(),
	likelihood: z.number().optional().default(-1),
	is_selected: z.boolean().default(true),
	justification: z.string().optional()
});

export const SecurityExceptionSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	owners: z.array(z.string().optional()).optional(),
	approver: z.string().optional().nullable(),
	severity: z.number().default(-1).optional(),
	status: z.string().default('draft'),
	expiration_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	requirement_assessments: z.string().optional().array().optional(),
	applied_controls: z.string().uuid().optional().array().optional()
});

export const FindingSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional(),
	owner: z.string().optional().array().optional(),
	status: z.string().default('--'),
	vulnerabilities: z.string().uuid().optional().array().optional(),
	applied_controls: z.string().uuid().optional().array().optional(),
	reference_controls: z.string().uuid().optional().array().optional(),
	findings_assessment: z.string(),
	severity: z.number().default(-1),
	filtering_labels: z.string().optional().array().optional()
});

export const FindingsAssessmentSchema = z.object({
	...NameDescriptionMixin,
	version: z.string().optional().default('0.1'),
	perimeter: z.string(),
	status: z.string().optional().nullable(),
	ref_id: z.string().optional(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	owner: z.string().optional().array().optional(),
	observation: z.string().optional().nullable(),
	category: z.string().default('--')
});

export const IncidentSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	status: z.string().default('new'),
	severity: z.number().default(6),
	threats: z.string().uuid().optional().array().optional(),
	owners: z.string().uuid().optional().array().optional(),
	assets: z.string().uuid().optional().array().optional(),
	qualifications: z.string().uuid().optional().array().optional()
});

export const TimelineEntrySchema = z.object({
	incident: z.string(),
	entry: z.string(),
	entry_type: z.string().default('observation'),
	timestamp: z
		.string()
		.datetime({ local: true })
		.refine((val) => !val || new Date(val) <= new Date(), {
			message: m.timestampCannotBeInTheFuture()
		}),
	observation: z.string().optional().nullable(),
	evidences: z.string().uuid().optional().array().optional()
});

export const TaskTemplateSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	status: z.string().default('pending'),
	assigned_to: z.string().optional().array().optional(),
	ref_id: z.string().optional(),
	task_date: z
		.string()
		.default(() => {
			const date = new Date();
			const year = date.getFullYear();
			const month = String(date.getMonth() + 1).padStart(2, '0'); // Months are zero-based
			const day = String(date.getDate()).padStart(2, '0');
			return `${year}-${month}-${day}`;
		})
		.optional(),
	is_recurrent: z.boolean().optional(),
	enabled: z.boolean().default(true).optional(),
	assets: z.string().uuid().optional().array().optional(),
	applied_controls: z.string().uuid().optional().array().optional(),
	compliance_assessments: z.string().uuid().optional().array().optional(),
	risk_assessments: z.string().uuid().optional().array().optional(),
	schedule: z
		.object({
			interval: z.number().min(1).positive().optional(),
			frequency: z.string().optional(),
			weeks_of_month: z.number().min(-1).max(4).array().optional(),
			days_of_week: z.number().min(1).max(7).array().optional(),
			months_of_year: z.number().min(1).max(12).array().optional(),
			end_date: z.union([z.literal('').transform(() => undefined), z.string().optional()])
		})
		.default({
			interval: 1,
			frequency: 'DAILY'
		})
		.optional()
});

export const TaskNodeSchema = z.object({
	due_date: z.string().optional(),
	status: z.string().optional(),
	observation: z.string().optional(),
	evidences: z.string().uuid().optional().array().optional()
});

const SCHEMA_MAP: Record<string, AnyZodObject> = {
	folders: FolderSchema,
	'folders-import': FolderImportSchema,
	perimeters: PerimeterSchema,
	'risk-matrices': RiskMatrixSchema,
	'risk-assessments': RiskAssessmentSchema,
	threats: ThreatSchema,
	'risk-scenarios': RiskScenarioSchema,
	'applied-controls': AppliedControlSchema,
	'applied-controls_duplicate': AppliedControlDuplicateSchema,
	policies: PolicySchema,
	'risk-acceptances': RiskAcceptanceSchema,
	'reference-controls': ReferenceControlSchema,
	assets: AssetSchema,
	'requirement-assessments': RequirementAssessmentSchema,
	'compliance-assessments': ComplianceAssessmentSchema,
	evidences: EvidenceSchema,
	users: UserCreateSchema,
	'sso-settings': SSOSettingsSchema,
	'general-settings': GeneralSettingsSchema,
	entities: EntitiesSchema,
	'entity-assessments': EntityAssessmentSchema,
	representatives: representativeSchema,
	solutions: solutionSchema,
	vulnerabilities: vulnerabilitySchema,
	'filtering-labels': FilteringLabelSchema,
	processings: processingSchema,
	purposes: purposeSchema,
	'personal-data': personalDataSchema,
	'data-subjects': dataSubjectSchema,
	'data-recipients': dataRecipientSchema,
	'data-contractors': dataContractorSchema,
	'data-transfers': dataTransferSchema,
	'ebios-rm': ebiosRMSchema,
	'feared-events': fearedEventsSchema,
	'ro-to': roToSchema,
	stakeholders: StakeholderSchema,
	'strategic-scenarios': StrategicScenarioSchema,
	'attack-paths': AttackPathSchema,
	'operational-scenarios': operationalScenarioSchema,
	'security-exceptions': SecurityExceptionSchema,
	findings: FindingSchema,
	'findings-assessments': FindingsAssessmentSchema,
	incidents: IncidentSchema,
	'timeline-entries': TimelineEntrySchema,
	'task-templates': TaskTemplateSchema,
	'task-nodes': TaskNodeSchema
};

export const modelSchema = (model: string) => {
	return SCHEMA_MAP[model] || z.object({});
};

export const composerSchema = z.object({
	risk_assessments: z.array(z.string().uuid())
});

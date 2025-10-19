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
	parent_folder: z.string().optional(),
	filtering_labels: z.array(z.string()).optional()
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
	lc_status: z.string().optional().default('in_design'),
	default_assignee: z.array(z.string().optional()).optional()
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
	version: z.string().optional().default('1.0'),
	perimeter: z.string(),
	status: z.string().optional().nullable(),
	ref_id: z.string().optional(),
	risk_matrix: z.string(),
	risk_tolerance: z.number().optional().default(-1),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	observation: z.string().optional().nullable(),
	ebios_rm_study: z.string().uuid().optional(),
	is_locked: z.boolean().optional().default(false)
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
	inherent_proba: z.number().optional(),
	inherent_impact: z.number().optional(),
	current_proba: z.number().optional(),
	current_impact: z.number().optional(),
	residual_proba: z.number().optional(),
	residual_impact: z.number().optional(),
	treatment: z.string().optional(),
	qualifications: z.string().uuid().optional().array().optional(),
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
	objectives: z.string().optional().array().optional(),
	assets: z.string().optional().array().optional(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	start_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	expiry_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
	effort: z.string().optional().nullable(),
	control_impact: z.number().optional().nullable(),
	cost: z
		.object({
			currency: z.enum(['€', '$', '£', '¥', 'C$', 'A$']).default('€'),
			amortization_period: z.number().min(1).max(50).default(1),
			build: z
				.object({
					fixed_cost: z.number().min(0).default(0),
					people_days: z.number().min(0).default(0)
				})
				.default({ fixed_cost: 0, people_days: 0 }),
			run: z
				.object({
					fixed_cost: z.number().min(0).default(0),
					people_days: z.number().min(0).default(0)
				})
				.default({ fixed_cost: 0, people_days: 0 })
		})
		.optional(),
	folder: z.string(),
	reference_control: z.string().optional().nullable(),
	owner: z.string().uuid().optional().array().optional(),
	security_exceptions: z.string().uuid().optional().array().optional(),
	stakeholders: z.string().uuid().optional().array().optional(),
	progress_field: z.number().optional().default(0),
	filtering_labels: z.string().optional().array().optional(),
	findings: z.string().uuid().optional().array().optional(),
	observation: z.string().optional().nullable()
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
	asset_class: z.string().optional(),
	parent_assets: z.string().optional().array().optional(),
	support_assets: z.string().optional().array().optional(),
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
	security_capabilities: z
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
	recovery_capabilities: z
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
	reference_link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),

	owner: z.string().uuid().optional().array().optional(),
	filtering_labels: z.string().optional().array().optional(),
	ebios_rm_studies: z.string().uuid().optional().array().optional(),
	security_exceptions: z.string().uuid().optional().array().optional(),
	ref_id: z.string().max(100).optional(),
	observation: z.string().optional().nullable(),
	overridden_children_capabilities: z.string().uuid().optional().array().optional()
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
	evidences: z.array(z.string().uuid().optional()).optional(),
	compliance_assessment: z.string(),
	applied_controls: z.array(z.string().uuid().optional()).optional(),
	observation: z.string().optional().nullable(),
	security_exceptions: z.string().uuid().optional().array().optional(),
	noRedirect: z.boolean().default(false)
});

export const UserEditSchema = z.object({
	email: z.string().email(),
	first_name: z.string().optional(),
	last_name: z.string().optional(),
	is_active: z.boolean().optional(),
	keep_local_login: z.boolean().optional(),
	user_groups: z.array(z.string().uuid().optional()).optional(),
	observation: z.string().optional().nullable(),
	expiry_date: z
		.union([z.literal('').transform(() => null), z.string().date()])
		.nullish()
		.refine(
			(val) => {
				if (!val) return true; // Allow null/undefined values
				const expiryDate = new Date(val);
				const today = new Date();
				today.setHours(0, 0, 0, 0); // Set to start of today to allow today's date
				return expiryDate >= today;
			},
			{
				message: 'Expiry date cannot be in the past'
			}
		)
});

export const UserCreateSchema = z.object({
	email: z.string().email(),
	observation: z.string().optional().nullable(),
	expiry_date: z
		.union([z.literal('').transform(() => null), z.string().date()])
		.nullish()
		.refine(
			(val) => {
				if (!val) return true; // Allow null/undefined values
				const expiryDate = new Date(val);
				const today = new Date();
				today.setHours(0, 0, 0, 0); // Set to start of today to allow today's date
				return expiryDate >= today;
			},
			{
				message: 'Expiry date cannot be in the past'
			}
		)
});

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
	version: z.string().optional().default('1.0'),
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
	assets: z.string().uuid().optional().array().optional(),
	evidences: z.string().uuid().optional().array().optional(),
	is_locked: z.boolean().optional().default(false)
});

export const CampaignSchema = z.object({
	...NameDescriptionMixin,
	frameworks: z.array(z.string()),
	selected_implementation_groups: z
		.array(z.object({ value: z.string(), framework: z.string() }))
		.optional(),
	perimeters: z.array(z.string()),
	status: z.string().optional().nullable(),
	start_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	folder: z.string()
});

export const EvidenceSchema = z.object({
	...NameDescriptionMixin,
	attachment: z.any().optional().nullable(),
	folder: z.string(),
	applied_controls: z.preprocess(toArrayPreprocessor, z.array(z.string().optional())).optional(),
	requirement_assessments: z.string().optional().array().optional(),
	findings: z.string().optional().array().optional(),
	findings_assessments: z
		.preprocess(toArrayPreprocessor, z.array(z.string().optional()))
		.optional(),
	timeline_entries: z.string().optional().array().optional(),

	link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
	filtering_labels: z.string().optional().array().optional(),
	owner: z.string().optional().array().optional(),
	status: z.string().optional().default('draft'),
	expiry_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish()
});

export const EvidenceRevisionSchema = z.object({
	folder: z.string().uuid(),
	evidence: z.string().uuid(),
	version: z.number().optional(),
	attachment: z.any().optional().nullable(),
	link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
	observation: z.string().optional().nullable()
});

export const GeneralSettingsSchema = z.object({
	security_objective_scale: z.string(),
	ebios_radar_green_zone_radius: z.number(),
	ebios_radar_yellow_zone_radius: z.number(),
	ebios_radar_red_zone_radius: z.number(),
	notifications_enable_mailing: z.boolean().optional(),
	interface_agg_scenario_matrix: z.boolean().optional(),
	risk_matrix_swap_axes: z.boolean().default(false).optional(),
	risk_matrix_flip_vertical: z.boolean().default(false).optional(),
	risk_matrix_labels: z.enum(['ISO', 'EBIOS']).default('ISO').optional(),
	currency: z.enum(['€', '$', '£', '¥', 'C$', 'A$']).default('€'),
	daily_rate: z.number().default(500).optional()
});

export const FeatureFlagsSchema = z.object({
	xrays: z.boolean().optional(),
	incidents: z.boolean().optional(),
	tasks: z.boolean().optional(),
	risk_acceptances: z.boolean().optional(),
	exceptions: z.boolean().optional(),
	follow_up: z.boolean().optional(),
	scoring_assistant: z.boolean().optional(),
	vulnerabilities: z.boolean().optional(),
	compliance: z.boolean().optional(),
	tprm: z.boolean().optional(),
	ebiosrm: z.boolean().optional(),
	privacy: z.boolean().optional(),
	experimental: z.boolean().optional(),
	inherent_risk: z.boolean().optional(),
	organisation_objectives: z.boolean().optional(),
	organisation_issues: z.boolean().optional(),
	quantitative_risk_studies: z.boolean().optional(),
	terminologies: z.boolean().optional(),
	bia: z.boolean().optional(),
	project_management: z.boolean().optional()
});

export const SSOSettingsSchema = z.object({
	is_enabled: z.boolean().default(false).optional(),
	force_sso: z.boolean().default(false).optional(),
	provider: z.string().default('saml'),
	provider_id: z.string().optional(),
	provider_name: z.string().optional(),
	client_id: z.string(),
	secret: z.string().optional(),

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
	want_name_id_encrypted: z.boolean().optional().nullable(),
	server_url: z.string().optional().nullable(),
	token_auth_method: z
		.enum([
			'client_secret_basic',
			'client_secret_post',
			'client_secret_jwt',
			'private_key_jwt',
			'none'
		])
		.optional()
		.nullable(),
	oauth_pkce_enabled: z.boolean().optional().default(false)
});

export const EntitiesSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	mission: z.string().optional(),
	reference_link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
	relationship: z.string().optional().array().optional()
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

export const BusinessImpactAnalysisSchema = z.object({
	...NameDescriptionMixin,
	version: z.string().optional().default('0.1'),
	perimeter: z.string(),
	status: z.string().optional().nullable(),
	ref_id: z.string().optional(),
	risk_matrix: z.string(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional()
});

export const AssetAssessmentSchema = z.object({
	bia: z.string(),
	asset: z.string(),
	associated_controls: z.array(z.string().optional()).optional(),
	dependencies: z.array(z.string().optional()).optional(),
	recovery_documented: z.boolean().default(false),
	recovery_tested: z.boolean().default(false),
	recovery_targets_met: z.boolean().default(false),
	evidences: z.array(z.string().optional()).optional(),
	observation: z.string().optional()
});

export const EscalationThresholdSchema = z.object({
	asset_assessment: z.string(),
	point_in_time: z.number(),
	qualifications: z.string().uuid().optional().array().optional(),
	quanti_impact_unit: z.string().optional().default('currency'),
	quali_impact: z.number().optional().default(-1),
	quanti_impact: z.number().optional(),
	justification: z.string().optional()
});
export const processingSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional().default(''),
	filtering_labels: z.string().optional().array().optional(),
	status: z.string().optional(),
	dpia_required: z.boolean().optional(),
	has_sensitive_personal_data: z.boolean().optional(),
	nature: z.string().optional().array().optional(),
	associated_controls: z.array(z.string().optional()).optional(),
	assigned_to: z.string().uuid().optional().array().optional()
});

export const rightRequestSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional().default(''),
	owner: z.string().uuid().optional().array().optional(),
	requested_on: z
		.string()
		.min(1)
		.default(() => new Date().toISOString().split('T')[0]),
	due_date: z.string().optional(),
	request_type: z.string(),
	status: z.string(),
	observation: z.string().optional(),
	processings: z.array(z.string()).optional().default([])
});

export const dataBreachSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional().default(''),
	assigned_to: z.string().uuid().optional().array().optional(),
	discovered_on: z
		.string()
		.min(1)
		.default(() => new Date().toISOString()),
	breach_type: z.string(),
	risk_level: z.string(),
	status: z.string(),
	affected_subjects_count: z.number().optional().default(0),
	affected_processings: z.array(z.string()).optional().default([]),
	affected_personal_data: z.array(z.string()).optional().default([]),
	affected_personal_data_count: z.number().optional().default(0),
	authorities: z.array(z.string()).optional().default([]),
	authority_notified_on: z.string().optional(),
	authority_notification_ref: z.string().optional(),
	subjects_notified_on: z.string().optional(),
	potential_consequences: z.string().optional(),
	remediation_measures: z.array(z.string()).optional().default([]),
	incident: z.string().optional(),
	reference_link: z.string().url().optional().or(z.literal('')),
	observation: z.string().optional()
});

export const purposeSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	legal_basis: z.string(),
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
	documentation_link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
	processing: z.string(),
	entity: z.string().optional()
});
export const dataTransferSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	country: z.string(),
	documentation_link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
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
	processing: z.string(),
	assets: z.string().uuid().optional().array().optional()
});

export const organisationObjectiveSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional().default(''),
	folder: z.string(),
	status: z.string().optional().default('draft'),
	health: z.string().optional(),
	assigned_to: z.string().optional().array().optional(),
	issues: z.string().uuid().optional().array().optional(),
	assets: z.string().uuid().optional().array().optional(),
	tasks: z.string().uuid().optional().array().optional(),
	observation: z.string().optional().nullable(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish()
});
export const organisationIssueSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional().default(''),
	observation: z.string().optional().nullable(),
	category: z.string().optional(),
	origin: z.string().optional(),
	assets: z.string().uuid().optional().array().optional()
});

export const quantitativeRiskStudySchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional(),
	status: z.string().optional().nullable(),
	distribution_model: z.string().optional().default('lognormal_ci90'),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	observation: z.string().optional().nullable(),
	risk_tolerance: z
		.object({
			points: z
				.object({
					point1: z
						.object({
							probability: z.number().min(0.01).max(0.99).optional(),
							acceptable_loss: z.number().min(1).optional()
						})
						.default({ probability: 0.99 })
						.optional(),
					point2: z
						.object({
							probability: z.number().min(0.01).max(0.99).optional(),
							acceptable_loss: z.number().min(1).optional()
						})
						.optional()
				})
				.optional(),
			curve_data: z
				.object({
					loss_values: z.array(z.number()).optional(),
					probability_values: z.array(z.number()).optional()
				})
				.optional()
		})
		.optional(),
	// .default({
	// 	points: { point1: { probability: 0.99, acceptable_loss: 1 }, point2: { probability: 0.01 } }
	// }),
	loss_threshold: z.number().optional().nullable(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	folder: z.string()
});

export const quantitativeRiskScenarioSchema = z.object({
	...NameDescriptionMixin,
	quantitative_risk_study: z.string().uuid(),
	assets: z.string().uuid().optional().array().optional(),
	owner: z.string().uuid().optional().array().optional(),
	priority: z.number().optional().nullable(),
	status: z.string().optional().default('draft'),
	vulnerabilities: z.string().uuid().optional().array().optional(),
	threats: z.string().uuid().optional().array().optional(),
	qualifications: z.string().uuid().optional().array().optional(),
	observation: z.string().optional().nullable(),
	is_selected: z.boolean().default(true),
	ref_id: z.string().optional()
});

export const quantitativeRiskHypothesisSchema = z.object({
	...NameDescriptionMixin,
	quantitative_risk_scenario: z.string().uuid(),
	existing_applied_controls: z.string().uuid().optional().array().optional(),
	added_applied_controls: z.string().uuid().optional().array().optional(),
	removed_applied_controls: z.string().uuid().optional().array().optional(),
	risk_stage: z.string().optional().default('residual'),
	ref_id: z.string().optional(),
	is_selected: z.boolean().default(true),
	probability: z.coerce.number().min(0).max(1).optional(),
	impact: z
		.object({
			distribution: z.string().default('LOGNORMAL-CI90'),
			lb: z.coerce.number().min(0).optional(),
			ub: z.coerce.number().min(0).optional()
		})
		.optional(),
	observation: z.string().optional().nullable(),
	filtering_labels: z.string().optional().array().optional()
});
export const ebiosRMSchema = z.object({
	...NameDescriptionMixin,
	version: z.string().optional().default('0.1'),
	quotation_method: z.string().optional().default('manual'),
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
	folder: z.string(),
	assets: z.string().uuid().optional().array().optional(),
	qualifications: z.string().uuid().optional().array().optional()
});

export const roToSchema = z.object({
	ebios_rm_study: z.string(),
	folder: z.string(),
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
	justification: z.string().optional(),
	folder: z.string()
});

export const StrategicScenarioSchema = z.object({
	...NameDescriptionMixin,
	ebios_rm_study: z.string(),
	ro_to_couple: z.string().uuid(),
	ref_id: z.string().optional(),
	folder: z.string()
});

export const AttackPathSchema = z.object({
	...NameDescriptionMixin,
	ebios_rm_study: z.string(),
	strategic_scenario: z.string().uuid(),
	stakeholders: z.string().uuid().optional().array().optional(),
	is_selected: z.boolean().default(true),
	justification: z.string().optional(),
	folder: z.string()
});

export const operationalScenarioSchema = z.object({
	ebios_rm_study: z.string(),
	attack_path: z.string().uuid(),
	threats: z.string().uuid().optional().array().optional(),
	operating_modes_description: z.string().optional(),
	likelihood: z.number().optional().default(-1),
	is_selected: z.boolean().default(true),
	justification: z.string().optional(),
	folder: z.string()
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
	filtering_labels: z.string().optional().array().optional(),
	evidences: z.string().uuid().optional().array().optional(),
	eta: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	due_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	observation: z.string().optional().nullable()
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
	category: z.string().default('--'),
	evidences: z.string().uuid().optional().array().optional(),
	is_locked: z.boolean().optional().default(false)
});

export const IncidentSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	reported_at: z
		.string()
		.datetime({ local: true })
		.refine((val) => !val || new Date(val) <= new Date(), {
			message: m.timestampCannotBeInTheFuture()
		})
		.optional(),
	ref_id: z.string().optional(),
	status: z.string().default('new'),
	detection: z.string().default('internally_detected'),
	severity: z.number().default(6),
	link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
	threats: z.string().uuid().optional().array().optional(),
	owners: z.string().uuid().optional().array().optional(),
	assets: z.string().uuid().optional().array().optional(),
	qualifications: z.string().uuid().optional().array().optional(),
	entities: z.string().uuid().optional().array().optional()
});

export const TimelineEntrySchema = z.object({
	folder: z.string(),
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
	applied_controls: z.preprocess(toArrayPreprocessor, z.array(z.string().optional())).optional(),
	compliance_assessments: z.string().uuid().optional().array().optional(),
	risk_assessments: z.string().uuid().optional().array().optional(),
	findings_assessment: z.string().uuid().optional().array().optional(),
	observation: z.string().optional(),
	evidences: z.string().uuid().optional().array().optional(),
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
		// Add cross-field validation for weeks_of_month and days_of_week (only for MONTHLY/YEARLY)
		.refine(
			(schedule) => {
				if (!schedule) return true;

				// Only apply this validation for MONTHLY and YEARLY frequencies
				if (schedule.frequency !== 'MONTHLY' && schedule.frequency !== 'YEARLY') {
					return true;
				}

				const hasWeeksOfMonth = schedule.weeks_of_month && schedule.weeks_of_month.length > 0;
				const hasDaysOfWeek = schedule.days_of_week && schedule.days_of_week.length > 0;

				// If weeks_of_month is provided, days_of_week must also be provided
				return !hasWeeksOfMonth || hasDaysOfWeek;
			},
			{
				message: m.daysOfWeekErrorMessage(),
				path: ['days_of_week']
			}
		)
		.refine(
			(schedule) => {
				if (!schedule) return true;

				// Only apply this validation for MONTHLY and YEARLY frequencies
				if (schedule.frequency !== 'MONTHLY' && schedule.frequency !== 'YEARLY') {
					return true;
				}

				const hasWeeksOfMonth = schedule.weeks_of_month && schedule.weeks_of_month.length > 0;
				const hasDaysOfWeek = schedule.days_of_week && schedule.days_of_week.length > 0;

				// If days_of_week is provided, weeks_of_month must also be provided
				return !hasDaysOfWeek || hasWeeksOfMonth;
			},
			{
				message: m.weeksOfMonthErrorMessage(),
				path: ['weeks_of_month']
			}
		),
	link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: 'Invalid URL format'
		})
		.optional()
});

export const TaskNodeSchema = z.object({
	due_date: z.string().optional(),
	status: z.string().optional(),
	observation: z.string().optional(),
	evidences: z.string().uuid().optional().array().optional()
});

export const AuthTokenCreateSchema = z.object({
	name: z.string().min(1),
	expiry: z.number().positive().min(1).max(365).default(30).optional()
});

export const ElementaryActionSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	threat: z.string().uuid().optional(),
	icon: z.string().optional().nullable(),
	attack_stage: z.number().default(0),
	operating_modes: z.string().uuid().optional().array().optional()
});

export const OperatingModeSchema = z.object({
	...NameDescriptionMixin,
	operational_scenario: z.string().uuid(),
	ref_id: z.string().optional(),
	elementary_actions: z.string().uuid().optional().array().optional(),
	likelihood: z.number().optional().default(-1),
	folder: z.string()
});

export const KillChainSchema = z.object({
	operating_mode: z.string().uuid(),
	elementary_action: z.string().uuid(),
	// is_highlighted: z.boolean().default(false),
	antecedents: z.string().uuid().optional().array().optional(),
	logic_operator: z.string().optional().nullable(),
	folder: z.string()
});

export const TerminologySchema = z.object({
	...NameDescriptionMixin,
	field_path: z.string().min(1),
	is_visible: z.boolean().default(true),
	translations: z.record(z.string().min(1), z.string().min(1))
});

export const RoleSchema = z.object({
	...NameDescriptionMixin,
	permissions: z.array(z.number()).optional()
});

// PMBOK
export const GenericCollectionSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	compliance_assessments: z.array(z.string().uuid().optional()).optional(),
	risk_assessments: z.array(z.string().uuid().optional()).optional(),
	crq_studies: z.array(z.string().uuid().optional()).optional(),
	ebios_studies: z.array(z.string().uuid().optional()).optional(),
	entity_assessments: z.array(z.string().uuid().optional()).optional(),
	findings_assessments: z.array(z.string().uuid().optional()).optional(),
	documents: z.array(z.string().uuid().optional()).optional(),
	security_exceptions: z.array(z.string().uuid().optional()).optional(),
	policies: z.array(z.string().uuid().optional()).optional(),
	dependencies: z.array(z.string().uuid().optional()).optional(),
	observation: z.string().optional().nullable(),
	filtering_labels: z.array(z.string().uuid().optional()).optional()
});

export const AccreditationSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	category: z.string().uuid(),
	authority: z.string().uuid().optional().nullable(),
	status: z.string().uuid(),
	author: z.string().uuid().optional().nullable(),
	expiry_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	linked_collection: z.string().uuid().optional().nullable(),
	checklist: z.string().uuid().optional().nullable(),
	observation: z.string().optional().nullable(),
	filtering_labels: z.array(z.string().uuid().optional()).optional()
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
	campaigns: CampaignSchema,
	evidences: EvidenceSchema,
	'evidence-revisions': EvidenceRevisionSchema,
	users: UserCreateSchema,
	'sso-settings': SSOSettingsSchema,
	'general-settings': GeneralSettingsSchema,
	'feature-flags': FeatureFlagsSchema,
	entities: EntitiesSchema,
	'entity-assessments': EntityAssessmentSchema,
	representatives: representativeSchema,
	solutions: solutionSchema,
	vulnerabilities: vulnerabilitySchema,
	'filtering-labels': FilteringLabelSchema,
	'business-impact-analysis': BusinessImpactAnalysisSchema,
	'asset-assessments': AssetAssessmentSchema,
	'escalation-thresholds': EscalationThresholdSchema,
	processings: processingSchema,
	'right-requests': rightRequestSchema,
	'data-breaches': dataBreachSchema,
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
	'task-nodes': TaskNodeSchema,
	'elementary-actions': ElementaryActionSchema,
	'operating-modes': OperatingModeSchema,
	'kill-chains': KillChainSchema,
	'organisation-objectives': organisationObjectiveSchema,
	'organisation-issues': organisationIssueSchema,
	'quantitative-risk-studies': quantitativeRiskStudySchema,
	'quantitative-risk-scenarios': quantitativeRiskScenarioSchema,
	'quantitative-risk-hypotheses': quantitativeRiskHypothesisSchema,
	terminologies: TerminologySchema,
	roles: RoleSchema,
	'generic-collections': GenericCollectionSchema,
	accreditations: AccreditationSchema
};

export const modelSchema = (model: string) => {
	return SCHEMA_MAP[model] || z.object({});
};

export const composerSchema = z.object({
	risk_assessments: z.array(z.string().uuid())
});

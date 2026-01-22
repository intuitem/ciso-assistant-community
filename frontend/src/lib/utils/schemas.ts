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
	parent_folder: z.string(),
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
	risk_origin: z.string().uuid().optional().nullable(),
	antecedent_scenarios: z.string().uuid().optional().array().optional(),
	filtering_labels: z.string().optional().array().optional(),
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
	requirement_assessments: z.string().optional().array().optional(),
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
			currency: z.enum(['€', '$', '£', '¥', 'C$', 'A$', 'NZ$', 'CHF']).default('€'),
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
	observation: z.string().optional().nullable(),
	integration_config: z.string().optional().nullable(),
	remote_object_id: z.string().optional().nullable(),
	create_remote_object: z.boolean().optional().default(false)
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

export const ValidationFlowSchema = z.object({
	folder: z.string(),
	ref_id: z.string().optional(),
	status: z.string().default('submitted'),
	validation_deadline: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	request_notes: z.string().optional().nullable(),
	approver: z.string(),
	filtering_labels: z.array(z.string().uuid().optional()).optional(),
	compliance_assessments: z.array(z.string()).optional(),
	risk_assessments: z.array(z.string()).optional(),
	business_impact_analysis: z.array(z.string()).optional(),
	crq_studies: z.array(z.string()).optional(),
	ebios_studies: z.array(z.string()).optional(),
	entity_assessments: z.array(z.string()).optional(),
	findings_assessments: z.array(z.string()).optional(),
	evidences: z.array(z.string()).optional(),
	security_exceptions: z.array(z.string()).optional(),
	policies: z.array(z.string()).optional()
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
	overridden_children_capabilities: z.string().uuid().optional().array().optional(),
	solutions: z.string().uuid().optional().array().optional(),
	applied_controls: z.string().uuid().optional().array().optional(),
	is_business_function: z.boolean().default(false),
	dora_licenced_activity: z.string().optional().nullable(),
	dora_criticality_assessment: z.string().default('eba_BT:x21'),
	dora_criticality_justification: z.string().optional().nullable(),
	dora_discontinuing_impact: z.string().default('eba_ZZ:x799')
});

export const FilteringLabelSchema = z.object({
	label: z.string()
});

export const RequirementAssessmentSchema = z.object({
	answers: jsonSchema,
	status: z.string(),
	result: z.string(),
	extended_result: z.string().optional().nullable(),
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
	extended_result_enabled: z.boolean().optional().default(false),
	progress_status_enabled: z.boolean().optional().default(true),
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
	contracts: z.preprocess(toArrayPreprocessor, z.array(z.string().optional())).optional(),
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
	task_node: z.string().uuid().nullable(),
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
	currency: z.enum(['€', '$', '£', '¥', 'C$', 'A$', 'NZ$', 'CHF']).default('€'),
	daily_rate: z.number().default(500).optional(),
	mapping_max_depth: z.coerce.number().int().min(2).max(5).default(3).optional(),
	allow_self_validation: z.boolean().default(false).optional(),
	show_warning_external_links: z.boolean().default(true).optional(),
	allow_assignments_to_entities: z.boolean().default(false).optional()
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
	project_management: z.boolean().optional(),
	contracts: z.boolean().optional(),
	reports: z.boolean().optional(),
	validation_flows: z.boolean().optional(),
	outgoing_webhooks: z.boolean().optional(),
	metrology: z.boolean().optional()
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
	sp_x509cert: z.string().optional(),
	sp_private_key: z.string().optional(),
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
	ref_id: z.string().optional(),
	is_active: z.boolean().optional(),
	parent_entity: z.string().optional().nullable(),
	mission: z.string().optional(),
	reference_link: z
		.string()
		.refine((val) => val === '' || (val.startsWith('http') && URL.canParse(val)), {
			message: "Link must be either empty or a valid URL starting with 'http'"
		})
		.optional(),
	relationship: z.string().optional().array().optional(),
	legal_identifiers: z.record(z.string()).optional(),
	country: z.string().nullish(),
	currency: z.string().nullish(),
	dora_entity_type: z.string().nullish(),
	dora_entity_hierarchy: z.string().nullish(),
	dora_assets_value: z.number().optional().nullable(),
	dora_competent_authority: z.string().optional(),
	dora_provider_person_type: z.string().nullish(),
	default_dependency: z.number().optional(),
	default_penetration: z.number().optional(),
	default_maturity: z.number().optional(),
	default_trust: z.number().optional(),
	filtering_labels: z.array(z.string()).optional()
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
	owner: z.string().uuid().optional().array().optional(),
	assets: z.string().uuid().optional().array().optional(),
	filtering_labels: z.string().optional().array().optional(),
	dora_ict_service_type: z.string().nullish(),
	storage_of_data: z.boolean().optional().default(false),
	data_location_storage: z.string().nullish(),
	data_location_processing: z.string().nullish(),
	dora_data_sensitiveness: z.string().nullish(),
	dora_reliance_level: z.string().nullish(),
	dora_substitutability: z.string().nullish(),
	dora_non_substitutability_reason: z.string().nullish(),
	dora_has_exit_plan: z.string().nullish(),
	dora_reintegration_possibility: z.string().nullish(),
	dora_discontinuing_impact: z.string().nullish(),
	dora_alternative_providers_identified: z.string().nullish(),
	dora_alternative_providers: z.string().optional()
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

export const contractSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	filtering_labels: z.array(z.string()).optional(),
	owner: z.array(z.string().optional()).optional(),
	provider_entity: z.string().optional(),
	beneficiary_entity: z.string().optional(),
	evidences: z.array(z.string().optional()).optional(),
	solutions: z.array(z.string().optional()).optional(),
	status: z.string().optional().default('draft'),
	start_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	end_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	ref_id: z.string().optional(),
	dora_contractual_arrangement: z.string().default('eba_CO:x1'),
	currency: z.string().optional(),
	annual_expense: z.number().optional().nullable(),
	termination_reason: z.string().optional(),
	is_intragroup: z.boolean().optional().default(false),
	overarching_contract: z.string().optional().nullable(),
	governing_law_country: z.string().optional(),
	notice_period_entity: z.number().optional().nullable(),
	notice_period_provider: z.number().optional().nullable()
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
	reviewers: z.array(z.string().optional()).optional(),
	is_locked: z.boolean().optional().default(false)
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
	dpia_reference: z.string().optional(),
	has_sensitive_personal_data: z.boolean().optional(),
	nature: z.string().optional().array().optional(),
	associated_controls: z.array(z.string().optional()).optional(),
	evidences: z.string().optional().array().optional(),
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
	metrics: z.string().uuid().optional().array().optional(),
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
	quotation_method: z.string().optional().default('express'),
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
	focused_feared_event: z.string().uuid().nullable().optional(),
	ref_id: z.string().optional(),
	folder: z.string()
});

export const AttackPathSchema = z.object({
	...NameDescriptionMixin,
	ref_id: z.string().optional(),
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
	folder: z.string(),
	strategic_scenario: z.string().optional()
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
	applied_controls: z.string().uuid().optional().array().optional(),
	assets: z.string().uuid().optional().array().optional(),
	observation: z.string().optional()
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
	priority: z.number().optional().nullable(),
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
	evidences: z.union([z.string().uuid(), z.string()]).optional().array().optional(), // Allow both UUIDs and strings for evidences created from the form
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

// Metrology
export const MetricDefinitionSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	category: z.string().default('quantitative'),
	unit: z.string().optional().nullable(),
	choices_definition: jsonSchema.optional().nullable(),
	provider: z.string().optional().nullable(),
	higher_is_better: z.boolean().default(true),
	default_target: z.number().optional().nullable(),
	filtering_labels: z.string().optional().array().optional()
});

export const MetricInstanceSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	metric_definition: z.string().uuid(),
	status: z.string().default('draft'),
	owner: z.array(z.string().uuid().optional()).optional(),
	target_value: z.coerce.number().optional().nullable(),
	collection_frequency: z.string().optional().nullable(),
	organisation_objectives: z.string().uuid().optional().array().optional(),
	filtering_labels: z.string().optional().array().optional()
});

export const CustomMetricSampleSchema = z.object({
	folder: z.string(),
	metric_instance: z.string().uuid(),
	timestamp: z.string().datetime(),
	value: jsonSchema
});

export const DashboardSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	ref_id: z.string().optional(),
	dashboard_definition: jsonSchema.default({}),
	filtering_labels: z.string().optional().array().optional()
});

export const DashboardWidgetSchema = z.object({
	folder: z.string(),
	dashboard: z.string().uuid(),
	// Custom metric (optional - either this or builtin fields)
	metric_instance: z.string().uuid().optional().nullable(),
	// Builtin metric fields (optional - either this or metric_instance)
	target_model: z.string().optional().nullable(),
	target_object_id: z.string().uuid().optional().nullable(),
	metric_key: z.string().optional().nullable(),
	// Text widget content (for chart_type='text')
	text_content: z.string().optional().nullable(),
	// Common fields
	title: z.string().optional().nullable(),
	position_x: z.coerce.number().min(0).max(11).default(0),
	position_y: z.coerce.number().min(0).default(0),
	width: z.coerce.number().min(1).max(12).default(6),
	height: z.coerce.number().min(1).default(2),
	chart_type: z.string().default('kpi_card'),
	time_range: z.string().default('last_30_days'),
	aggregation: z.string().default('none'),
	show_target: z.boolean().default(true),
	show_legend: z.boolean().default(true),
	widget_config: jsonSchema.default({})
});

export const teamSchema = z.object({
	...NameDescriptionMixin,
	team_email: z.string().email().optional(),
	folder: z.string(),
	members: z.array(z.string().uuid().optional()).optional(),
	leader: z.string().uuid(),
	deputies: z.array(z.string().uuid().optional()).optional()
});

// ============================================================================
// Base Aggregate Schema (matches backend/core/domain/aggregate.py)
// ============================================================================

/** Base fields for DDD aggregates (from AggregateRoot) - for read operations */
export const AggregateBaseSchema = z.object({
	id: z.string().uuid(),
	version: z.number().int().min(0),
	created_at: z.string().datetime(),
	updated_at: z.string().datetime(),
	created_by: z.string().uuid().nullable(),
	updated_by: z.string().uuid().nullable()
});

/** Audit fields mixin for create/update forms */
const AuditFieldsMixin = {
	created_by: z.string().uuid().optional().nullable(),
	updated_by: z.string().uuid().optional().nullable()
};

// ============================================================================
// RMF Operations Schemas (matches backend/core/bounded_contexts/rmf_operations/)
// ============================================================================

/** STIG checklist lifecycle state */
const STIGChecklistLifecycleEnum = z.enum(['draft', 'active', 'archived']);

/** STIG checklist asset type */
const STIGChecklistAssetTypeEnum = z.enum([
	'computing',
	'network',
	'storage',
	'application',
	'database',
	'web_server',
	'other'
]);

/** STIG finding status */
const STIGFindingStatusEnum = z.enum(['open', 'not_a_finding', 'not_applicable', 'not_reviewed']);

/** STIG severity category */
const STIGSeverityEnum = z.enum(['cat1', 'cat2', 'cat3']);

/** Asset metadata schema (matches rmf_enhanced.AssetMetadata) */
export const AssetMetadataSchema = z.object({
	hostname: z.string().min(1),
	ip_addresses: z.array(z.string()).default([]),
	mac_addresses: z.array(z.string()).default([]),
	fqdn: z.string().default(''),
	technology_area: z.string().default(''),
	asset_type: z.string().default('computing'),
	role: z.string().default(''),
	operating_system: z.string().default(''),
	os_version: z.string().default(''),
	location: z.string().default(''),
	department: z.string().default(''),
	system_administrator: z.string().default(''),
	is_internet_facing: z.boolean().default(false),
	classification: z.string().default('unclassified')
});

/** STIG vulnerability finding schema */
export const STIGFindingSchema = z.object({
	vuln_id: z.string().min(1),
	rule_id: z.string().min(1),
	stig_id: z.string().min(1),
	severity: STIGSeverityEnum,
	status: STIGFindingStatusEnum,
	finding_details: z.string().default(''),
	comments: z.string().default(''),
	cci_ids: z.array(z.string()).default([]),
	check_content: z.string().default(''),
	fix_text: z.string().default(''),
	rule_title: z.string().default(''),
	discussion: z.string().default(''),
	false_positives: z.string().default(''),
	false_negatives: z.string().default(''),
	documentable: z.boolean().default(true),
	mitigations: z.string().default(''),
	severity_override: z.string().default(''),
	severity_override_guidance: z.string().default(''),
	potential_impacts: z.string().default(''),
	third_party_tools: z.string().default(''),
	ia_controls: z.string().default('')
});

/** STIG checklist schema (matches aggregates/stig_checklist.py) */
export const STIGChecklistSchema = z.object({
	// Basic info
	name: nameSchema,
	description: descriptionSchema,
	folder: z.string(),

	// Identity and system relationship
	systemGroupId: z.string().uuid().optional().nullable(),
	hostName: z.string().min(1),

	// STIG metadata
	stigType: z.string().min(1),
	stigRelease: z.string().default(''),
	version: z.string().default(''),

	// Lifecycle
	lifecycle_state: STIGChecklistLifecycleEnum.default('draft'),

	// Asset information
	assetInfo: jsonSchema.optional(),

	// Web/Database specific fields (OpenRMF naming convention)
	isWebDatabase: z.boolean().default(false),
	webDatabaseSite: z.string().default(''),
	webDatabaseInstance: z.string().default(''),

	// Asset type classification
	asset_type: STIGChecklistAssetTypeEnum.default('computing'),

	// Metadata
	tags: z.array(z.string()).default([]),

	// Legacy/convenience fields for backwards compatibility
	stig_id: z.string().optional(),
	stig_version: z.string().optional(),
	release_info: z.string().optional(),
	classification: z.string().default('unclassified'),
	asset: AssetMetadataSchema.optional(),

	// Audit fields
	...AuditFieldsMixin
});

/** Vulnerability finding schema (matches aggregates/vulnerability_finding.py) */
export const VulnerabilityFindingSchema = z.object({
	// Identity and relationships
	checklistId: z.string().uuid(),
	vulnId: z.string().min(1),
	stigId: z.string().min(1),
	ruleId: z.string().min(1),

	// Vulnerability details
	ruleTitle: z.string().min(1),
	ruleDiscussion: z.string().default(''),
	checkContent: z.string().default(''),
	fixText: z.string().default(''),

	// Status and severity
	status_data: z.object({
		status: STIGFindingStatusEnum.default('not_reviewed'),
		finding_details: z.string().nullable().default(null),
		comments: z.string().nullable().default(null),
		severity_override: z.string().nullable().default(null),
		severity_justification: z.string().nullable().default(null)
	}).default({}),
	severity_category: STIGSeverityEnum,

	// Additional metadata
	ruleVersion: z.string().default(''),
	cciIds: z.array(z.string()).default([]),

	// Metadata
	tags: z.array(z.string()).default([]),

	// Audit fields
	...AuditFieldsMixin
});

/** Nessus scan processing status */
const NessusScanProcessingStatusEnum = z.enum(['uploaded', 'processing', 'completed', 'failed']);

/** Nessus scan schema (matches aggregates/nessus_scan.py) */
export const NessusScanSchema = z.object({
	systemGroupId: z.string().uuid(),
	folder: z.string(),

	// File information
	filename: z.string().min(1),

	// Scan metadata (extracted from XML, optional on creation)
	scan_date: z.union([z.literal('').transform(() => null), z.string().datetime()]).nullish(),
	scanner_version: z.string().optional().nullable(),
	policy_name: z.string().optional().nullable(),

	// Statistics (computed, optional on creation)
	total_hosts: z.number().int().min(0).default(0),
	total_vulnerabilities: z.number().int().min(0).default(0),
	scan_duration_seconds: z.number().int().min(0).optional().nullable(),

	// Severity breakdown
	critical_count: z.number().int().min(0).default(0),
	high_count: z.number().int().min(0).default(0),
	medium_count: z.number().int().min(0).default(0),
	low_count: z.number().int().min(0).default(0),
	info_count: z.number().int().min(0).default(0),

	// Correlation data
	correlated_checklist_ids: z.array(z.string().uuid()).default([]),

	// Additional metadata
	tags: z.array(z.string()).default([]),

	// Processing status
	processing_status: NessusScanProcessingStatusEnum.default('uploaded'),
	processing_error: z.string().optional().nullable(),

	// Audit fields
	...AuditFieldsMixin
});

/** Checklist score schema (matches aggregates/checklist_score.py) */
export const ChecklistScoreSchema = z.object({
	// Identity
	checklistId: z.string().uuid(),
	systemGroupId: z.string().uuid().optional().nullable(),

	// Host information (denormalized for queries)
	hostName: z.string().min(1),
	stigType: z.string().min(1),

	// Category 1 (High/CAT I) counts
	totalCat1Open: z.number().int().min(0).default(0),
	totalCat1NotAFinding: z.number().int().min(0).default(0),
	totalCat1NotApplicable: z.number().int().min(0).default(0),
	totalCat1NotReviewed: z.number().int().min(0).default(0),

	// Category 2 (Medium/CAT II) counts
	totalCat2Open: z.number().int().min(0).default(0),
	totalCat2NotAFinding: z.number().int().min(0).default(0),
	totalCat2NotApplicable: z.number().int().min(0).default(0),
	totalCat2NotReviewed: z.number().int().min(0).default(0),

	// Category 3 (Low/CAT III) counts
	totalCat3Open: z.number().int().min(0).default(0),
	totalCat3NotAFinding: z.number().int().min(0).default(0),
	totalCat3NotApplicable: z.number().int().min(0).default(0),
	totalCat3NotReviewed: z.number().int().min(0).default(0),

	// Legacy/convenience fields for backwards compatibility
	checklist_id: z.string().uuid().optional(),
	checklist_name: z.string().optional(),
	cat1_open: z.number().int().min(0).optional(),
	cat1_closed: z.number().int().min(0).optional(),
	cat2_open: z.number().int().min(0).optional(),
	cat2_closed: z.number().int().min(0).optional(),
	cat3_open: z.number().int().min(0).optional(),
	cat3_closed: z.number().int().min(0).optional(),
	compliance_percentage: z.number().min(0).max(100).optional(),

	// Audit fields
	...AuditFieldsMixin
});

/** System group lifecycle state */
const SystemGroupLifecycleEnum = z.enum(['draft', 'active', 'archived']);

/** System group schema (matches aggregates/system_group.py) */
export const SystemGroupSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),

	// Lifecycle
	lifecycle_state: SystemGroupLifecycleEnum.default('draft'),

	// Embedded ID arrays (optional for creation)
	checklistIds: z.array(z.string().uuid()).default([]),
	assetIds: z.array(z.string().uuid()).default([]),
	nessusScanIds: z.array(z.string().uuid()).default([]),

	// Asset hierarchy and relationships
	asset_hierarchy: jsonSchema.optional(),

	// Compliance tracking
	last_compliance_check: z
		.union([z.literal('').transform(() => null), z.string().datetime()])
		.nullish(),

	// Metadata
	tags: z.array(z.string()).default([]),

	// Computed fields (read-only, not for form submission)
	totalChecklists: z.number().int().min(0).optional(),
	totalOpenVulnerabilities: z.number().int().min(0).optional(),
	totalCat1Open: z.number().int().min(0).optional(),
	totalCat2Open: z.number().int().min(0).optional(),
	totalCat3Open: z.number().int().min(0).optional(),

	// Legacy/convenience fields for backwards compatibility
	system_identifier: z.string().optional(),
	impact_level: z.enum(['LOW', 'MODERATE', 'HIGH']).default('MODERATE'),
	authorization_status: z.enum(['ato', 'dato', 'iato', 'denied', 'pending']).default('pending'),
	ato_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	ato_expiration: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),

	// Audit fields
	...AuditFieldsMixin
});

// ============================================================================
// OSCAL Integration Schemas (matches backend/oscal_integration/services/)
// ============================================================================

/** OSCAL model type */
const OscalModelTypeEnum = z.enum([
	'catalog',
	'profile',
	'component-definition',
	'ssp',
	'assessment-plan',
	'assessment-results',
	'poam'
]);

/** OSCAL document schema */
export const OscalDocumentSchema = z.object({
	name: nameSchema,
	description: descriptionSchema,
	document_type: OscalModelTypeEnum,
	oscal_version: z.string().default('1.1.2'),
	content: jsonSchema,
	folder: z.string()
});

// ============================================================================
// FedRAMP Schemas (matches backend/oscal_integration/services/fedramp_enhanced.py)
// ============================================================================

/** FedRAMP control origination */
const ControlOriginationEnum = z.enum([
	'sp-corporate',
	'sp-system',
	'customer-configured',
	'customer-provided',
	'inherited',
	'shared',
	'hybrid'
]);

/** FedRAMP implementation status */
const FedRAMPImplementationStatusEnum = z.enum([
	'implemented',
	'partially-implemented',
	'planned',
	'alternative-implementation',
	'not-applicable'
]);

/** FedRAMP baseline */
const FedRAMPBaselineEnum = z.enum(['LOW', 'MODERATE', 'HIGH', 'LI_SAAS']);

/** Control origination info schema */
export const ControlOriginationSchema = z.object({
	control_id: z.string().min(1),
	originations: z.array(ControlOriginationEnum).min(1),
	description: z.string().default(''),
	responsible_roles: z.array(z.string()).default([]),
	implementation_status: FedRAMPImplementationStatusEnum.default('planned')
});

/** FedRAMP responsible role schema */
export const FedRAMPRoleSchema = z.object({
	role_id: z.string().min(1),
	title: z.string().min(1),
	description: z.string().default(''),
	party_uuids: z.array(z.string().uuid()).default([])
});

// ============================================================================
// POA&M Schemas (matches backend/poam/services/poam_export.py)
// ============================================================================

/** POA&M deviation type */
const POAMDeviationTypeEnum = z.enum(['OR', 'FR', 'FP', 'VENDOR_DEPENDENCY']);

/** POA&M risk level */
const POAMRiskLevelEnum = z.enum(['HIGH', 'MODERATE', 'LOW']);

/** POA&M status */
const POAMStatusEnum = z.enum(['open', 'completed', 'in_progress', 'delayed']);

/** POA&M milestone schema */
export const POAMMilestoneSchema = z.object({
	description: z.string().min(1),
	due_date: z.string().date(),
	completion_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	status: z.enum(['open', 'completed', 'in_progress']).default('open')
});

/** POA&M item schema */
export const POAMItemSchema = z.object({
	poam_id: z.string().min(1),
	weakness_name: z.string().min(1),
	weakness_description: z.string().default(''),
	detector_source: z.string().default(''),
	source_id: z.string().default(''),
	asset_identifier: z.string().default(''),
	point_of_contact: z.string().default(''),
	resources_required: z.string().default(''),
	scheduled_completion_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	milestones: z.array(POAMMilestoneSchema).default([]),
	milestone_changes: z.string().default(''),
	status: POAMStatusEnum.default('open'),
	comments: z.string().default(''),
	control_id: z.string().default(''),
	original_risk_rating: POAMRiskLevelEnum.default('MODERATE'),
	adjusted_risk_rating: POAMRiskLevelEnum.optional(),
	risk_adjustment: z.string().default(''),
	false_positive: z.boolean().default(false),
	operational_requirement: z.boolean().default(false),
	deviation_type: POAMDeviationTypeEnum.nullish(),
	deviation_rationale: z.string().default(''),
	vendor_dependency: z.boolean().default(false),
	vendor_product_name: z.string().default(''),
	vendor_checkin_date: z.union([z.literal('').transform(() => null), z.string().date()]).nullish(),
	supporting_documents: z.array(z.string()).default([]),
	auto_approve: z.boolean().default(false),
	folder: z.string()
});

// ============================================================================
// Questionnaire Enhanced Schemas (matches backend/questionnaires/services/govready_enhanced.py)
// ============================================================================

/** Condition operator */
const ConditionOperatorEnum = z.enum([
	'equals',
	'not_equals',
	'contains',
	'not_contains',
	'greater_than',
	'less_than',
	'greater_or_equal',
	'less_or_equal',
	'is_empty',
	'is_not_empty',
	'matches',
	'in',
	'not_in'
]);

/** Questionnaire module schema */
export const QuestionnaireModuleSchema = z.object({
	module_id: z.string().min(1),
	title: z.string().min(1),
	description: z.string().default(''),
	version: z.string().default('1.0'),
	framework: z.string().optional(),
	questions: z.array(
		z.object({
			id: z.string().min(1),
			prompt: z.string().min(1),
			type: z.enum(['text', 'choice', 'multiple-choice', 'boolean', 'date', 'number']),
			choices: z.array(z.string()).optional(),
			required: z.boolean().default(false),
			conditional_logic: jsonSchema.optional()
		})
	).default([]),
	control_mappings: z.record(z.array(z.string())).default({})
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
	'validation-flows': ValidationFlowSchema,
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
	contracts: contractSchema,
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
	accreditations: AccreditationSchema,
	'metric-definitions': MetricDefinitionSchema,
	'metric-instances': MetricInstanceSchema,
	'custom-metric-samples': CustomMetricSampleSchema,
	dashboards: DashboardSchema,
	'dashboard-widgets': DashboardWidgetSchema,
	'dashboard-text-widgets': DashboardWidgetSchema,
	'dashboard-builtin-widgets': DashboardWidgetSchema,
	teams: teamSchema,
	// RMF Operations
	'stig-checklists': STIGChecklistSchema,
	'stig-findings': STIGFindingSchema,
	'vulnerability-findings': VulnerabilityFindingSchema,
	'checklist-scores': ChecklistScoreSchema,
	'system-groups': SystemGroupSchema,
	'nessus-scans': NessusScanSchema,
	// OSCAL Integration
	'oscal-documents': OscalDocumentSchema,
	// FedRAMP
	'control-originations': ControlOriginationSchema,
	'fedramp-roles': FedRAMPRoleSchema,
	// POA&M
	'poam-items': POAMItemSchema,
	'poam-milestones': POAMMilestoneSchema,
	// Questionnaires Enhanced
	'questionnaire-modules': QuestionnaireModuleSchema
};

export const modelSchema = (model: string) => {
	return SCHEMA_MAP[model] || z.object({});
};

export const composerSchema = z.object({
	risk_assessments: z.array(z.string().uuid())
});

export const webhookEndpointSchema = z.object({
	...NameDescriptionMixin,
	url: z.string().url(),
	event_types: z.string().array().nonempty(),
	is_active: z.boolean().default(true),
	secret: z.string().min(1).optional(),
	target_folders: z.string().uuid().optional().array().optional(),
	payload_format: z.enum(['thin', 'full']).default('full')
});

export const dataAssetSchema = z.object({
	asset_id: z.string().nonempty(),
	asset_name: z.string().nonempty(),
	asset_description: z.string().optional(),
	primary_data_category: z.enum([
		'personal_data',
		'sensitive_personal_data',
		'special_category_data',
		'criminal_conviction_data',
		'genetic_data',
		'biometric_data',
		'health_data',
		'financial_data',
		'communication_data',
		'location_data',
		'online_identifier_data',
		'racial_ethnic_data',
		'political_opinion_data',
		'religious_belief_data',
		'trade_union_data',
		'sexual_orientation_data'
	]),
	data_categories: z.array(z.string()).optional(),
	sensitivity_level: z.enum(['public', 'internal', 'confidential', 'restricted', 'highly_restricted']),
	data_subject_types: z.array(z.string()).optional(),
	estimated_data_subjects: z.number().int().min(0).optional(),
	processing_purposes: z.array(z.string()).optional(),
	legal_bases: z.array(z.string()).optional(),
	legitimate_interests: z.string().optional(),
	storage_locations: z.array(z.string()).optional(),
	retention_schedule: z.string().optional(),
	retention_period_days: z.number().int().min(0).optional(),
	disposal_methods: z.array(z.string()).optional(),
	recipients: z.array(z.string()).optional(),
	third_party_processors: z.array(z.string()).optional(),
	security_measures: z.array(z.string()).optional(),
	encryption_methods: z.array(z.string()).optional(),
	access_controls: z.array(z.string()).optional(),
	pia_required: z.boolean().default(false),
	dpo_review_required: z.boolean().default(false),
	tags: z.array(z.string()).optional()
});

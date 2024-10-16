// schema for the validation of forms
import { z, type AnyZodObject } from 'zod';

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
	parent_folder: z.string().optional()
});

export const ProjectSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	internal_reference: z.string().optional().nullable(),
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
	project: z.string(),
	status: z.string().optional().nullable(),
	risk_matrix: z.string(),
	eta: z.string().optional().nullable(),
	due_date: z.string().optional().nullable(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	observation: z.string().optional().nullable()
});

export const ThreatSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	provider: z.string().optional().nullable(),
	ref_id: z.string().optional().nullable(),
	annotation: z.string().optional().nullable()
});

export const RiskScenarioSchema = z.object({
	...NameDescriptionMixin,
	existing_controls: z.string().optional(),
	applied_controls: z.string().uuid().optional().array().optional(),
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
	owner: z.string().uuid().optional().array().optional()
});

export const AppliedControlSchema = z.object({
	...NameDescriptionMixin,
	category: z.string().optional().nullable(),
	csf_function: z.string().optional().nullable(),
	status: z.string().optional().default('--'),
	evidences: z.string().optional().array().optional(),
	eta: z.string().optional().nullable(),
	start_date: z.string().optional().nullable(),
	expiry_date: z.string().optional().nullable(),
	link: z.string().url().optional().or(z.literal('')),
	effort: z.string().optional().nullable(),
	cost: z.number().multipleOf(0.000001).optional().nullable(),
	folder: z.string(),
	reference_control: z.string().optional().nullable(),
	owner: z.string().uuid().optional().array().optional()
});

export const AppliedControlDuplicateSchema = z.object({
	...AppliedControlSchema.shape,
	duplicate_evidences: z.boolean()
});

export const PolicySchema = z.object({
	...NameDescriptionMixin,
	csf_function: z.string().optional().nullable(),
	status: z.string().optional().default('--'),
	evidences: z.string().optional().array().optional(),
	eta: z.string().optional().nullable(),
	expiry_date: z.string().optional().nullable(),
	link: z.string().url().optional().or(z.literal('')),
	effort: z.string().optional().nullable(),
	folder: z.string(),
	reference_control: z.string().optional().nullable()
});

export const RiskAcceptanceSchema = z.object({
	...NameDescriptionMixin,
	folder: z.string(),
	expiry_date: z.string().optional().nullable(),
	justification: z.string().optional().nullable(),
	approver: z.string(),
	risk_scenarios: z.array(z.string())
});

export const ReferenceControlSchema = z.object({
	...NameDescriptionMixin,
	provider: z.string().optional().nullable(),
	category: z.string().optional().nullable(),
	csf_function: z.string().optional().nullable(),
	folder: z.string(),
	ref_id: z.string().optional().nullable(),
	annotation: z.string().optional().nullable()
});

export const AssetSchema = z.object({
	...NameDescriptionMixin,
	business_value: z.string().optional(),
	type: z.string().default('PR'),
	folder: z.string(),
	parent_assets: z.string().optional().array().optional()
});

export const RequirementAssessmentSchema = z.object({
	answer: jsonSchema,
	status: z.string(),
	result: z.string(),
	score: z.number().optional().nullable(),
	is_scored: z.boolean().optional(),
	comment: z.string().optional().nullable(),
	folder: z.string(),
	requirement: z.string(),
	evidences: z.array(z.string().uuid().optional()).optional(),
	compliance_assessment: z.string(),
	applied_controls: z.array(z.string().uuid().optional()).optional(),
	observation: z.string().optional().nullable()
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
	version: z.string().optional().default('0.1'),
	project: z.string(),
	status: z.string().optional().nullable(),
	selected_implementation_groups: z.array(z.string().optional()).optional(),
	framework: z.string(),
	eta: z.string().optional().nullable(),
	due_date: z.string().optional().nullable(),
	authors: z.array(z.string().optional()).optional(),
	reviewers: z.array(z.string().optional()).optional(),
	baseline: z.string().optional().nullable(),
	create_applied_controls_from_suggestions: z.boolean().optional().default(false),
	observation: z.string().optional().nullable()
});

export const EvidenceSchema = z.object({
	...NameDescriptionMixin,
	attachment: z.any().optional().nullable(),
	folder: z.string(),
	applied_controls: z.preprocess(toArrayPreprocessor, z.array(z.string().optional())).optional(),
	requirement_assessments: z.string().optional().array().optional(),
	link: z.string().optional().nullable()
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
	reference_link: z.string().optional()
});

export const EntityAssessmentSchema = z.object({
	...NameDescriptionMixin,
	create_audit: z.boolean().optional().default(false),
	framework: z.string().optional(),
	selected_implementation_groups: z.array(z.string().optional()).optional(),
	version: z.string().optional().default('0.1'),
	project: z.string(),
	status: z.string().optional().nullable(),
	eta: z.string().optional().nullable(),
	due_date: z.string().optional().nullable(),
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
	criticality: z.number().optional()
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

const SCHEMA_MAP: Record<string, AnyZodObject> = {
	folders: FolderSchema,
	projects: ProjectSchema,
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
	entities: EntitiesSchema,
	'entity-assessments': EntityAssessmentSchema,
	representatives: representativeSchema,
	solutions: solutionSchema
};

export const modelSchema = (model: string) => {
	return SCHEMA_MAP[model] || z.object({});
};

export const composerSchema = z.object({
	risk_assessments: z.array(z.string().uuid())
});

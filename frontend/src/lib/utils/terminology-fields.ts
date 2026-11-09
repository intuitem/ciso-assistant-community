// Mirrors Terminology.FieldPath; values map to their label's message key.
export const TERMINOLOGY_FIELDS = {
	'ro_to.risk_origin': 'riskOrigin',
	'ro_to.target_objective_category': 'targetObjectiveCategory',
	qualifications: 'qualifications',
	'accreditation.status': 'accreditationStatus',
	'accreditation.category': 'accreditationCategory',
	'entity.relationship': 'entityRelationship',
	'metric_definition.unit': 'metricUnit',
	'project.status': 'projectStatus',
	'project.health': 'projectHealth',
	'processing.nature': 'processingNature',
	'personal_data.category': 'personalDataCategory',
	'entity_score.provider': 'entityScoreProvider',
	'asset.lifecycle_stage': 'assetLifecycleStage'
} as const;

export type TerminologyField = keyof typeof TERMINOLOGY_FIELDS;

export const isTerminologyField = (param: string): param is TerminologyField =>
	Object.hasOwn(TERMINOLOGY_FIELDS, param);

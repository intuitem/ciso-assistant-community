// Curated map of object type → url-model, shared by the preset editor (journey step
// targets / scaffolds) and the portal editor (create-tile target picker).
export const TYPE_TO_MODEL: Record<string, string> = {
	compliance_assessment: 'compliance-assessments',
	risk_assessment: 'risk-assessments',
	business_impact_analysis: 'business-impact-analysis',
	findings_assessment: 'findings-assessments',
	ebios_rm_study: 'ebios-rm',
	processing: 'processings',
	entity: 'entities',
	task_template: 'task-templates',
	organisation_objective: 'organisation-objectives',
	organisation_issue: 'organisation-issues',
	perimeter: 'perimeters',
	asset: 'assets',
	applied_control: 'applied-controls',
	policy: 'policies',
	security_exception: 'security-exceptions',
	risk_acceptance: 'risk-acceptances',
	incident: 'incidents',
	vulnerability: 'vulnerabilities',
	project: 'projects',
	responsibility_matrix: 'responsibility-matrices'
};

export const MODEL_TO_TYPE: Record<string, string> = Object.fromEntries(
	Object.entries(TYPE_TO_MODEL).map(([t, m]) => [m, t])
);

export const SCAFFOLD_TYPES = Object.keys(TYPE_TO_MODEL);

export const SCAFFOLDABLE_MODELS = Object.values(TYPE_TO_MODEL);

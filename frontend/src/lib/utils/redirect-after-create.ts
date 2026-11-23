// Models whose detail page is where the work happens: creating one opens it.
// threat-models stays out: the quantitative risk scenario form creates them inline.
export const REDIRECT_AFTER_CREATE = new Set<string>([
	'compliance-assessments',
	'risk-assessments',
	'entity-assessments',
	'quantitative-risk-studies',
	'quantitative-risk-scenarios',
	'quantitative-risk-hypotheses',
	'document-containers',
	'metric-instances',
	'ebios-rm',
	'business-impact-analysis',
	'campaigns',
	'findings-assessments',
	'posture-assessments',
	'responsibility-matrices',
	'dashboards',
	'workflows',
	'processings',
	'projects',
	'incidents'
]);

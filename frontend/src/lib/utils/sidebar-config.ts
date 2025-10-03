type SidebarBackendKeys = {
	xrays: boolean;
	incidents: boolean;
	tasks: boolean;
	risk_acceptances: boolean;
	exceptions: boolean;
	follow_up: boolean;
	ebiosrm: boolean;
	scoring_assistant: boolean;
	vulnerabilities: boolean;
	compliance: boolean;
	tprm: boolean;
	privacy: boolean;
	experimental: boolean;
	organisation_objectives: boolean;
	organisation_issues: boolean;
	quantitative_risk_studies: boolean;
	terminologies: boolean;
	bia: boolean;
	project_management: boolean;
};

type SidebarFrontendKeys = {
	xRays: boolean;
	incidents: boolean;
	tasks: boolean;
	riskAcceptances: boolean;
	securityExceptions: boolean;
	followUp: boolean;
	ebiosRM: boolean;
	scoringAssistant: boolean;
	vulnerabilities: boolean;
	compliance: boolean;
	thirdPartyCategory: boolean;
	privacy: boolean;
	experimental: boolean;
	organisationObjectives: boolean;
	organisationIssues: boolean;
	quantitativeRiskStudies: boolean;
	terminologies: boolean;
	businessImpactAnalysis: boolean;
	projectManagement: boolean;
};

export function getSidebarVisibleItems(
	featureFlags: Partial<SidebarBackendKeys>
): SidebarFrontendKeys {
	return {
		xRays: featureFlags?.xrays ?? false,
		incidents: featureFlags?.incidents ?? false,
		tasks: featureFlags?.tasks ?? false,
		riskAcceptances: featureFlags?.risk_acceptances ?? false,
		securityExceptions: featureFlags?.exceptions ?? false,
		followUp: featureFlags?.follow_up ?? false,
		ebiosRM: featureFlags?.ebiosrm ?? false,
		scoringAssistant: featureFlags?.scoring_assistant ?? false,
		vulnerabilities: featureFlags?.vulnerabilities ?? false,
		compliance: featureFlags?.compliance ?? false,
		thirdPartyCategory: featureFlags?.tprm ?? false,
		privacy: featureFlags?.privacy ?? false,
		experimental: featureFlags?.experimental ?? false,
		organisationObjectives: featureFlags?.organisation_objectives ?? false,
		organisationIssues: featureFlags?.organisation_issues ?? false,
		quantitativeRiskStudies: featureFlags?.quantitative_risk_studies ?? false,
		terminologies: featureFlags?.terminologies ?? true,
		businessImpactAnalysis: featureFlags?.bia ?? true,
		projectManagement: featureFlags?.project_management ?? false
	};
}

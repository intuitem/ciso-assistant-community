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
};

type SidebarFrontendVisibility = {
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
	Experimental: boolean;
};

export function getSidebarVisibilityFromBackend(
	featureFlags: Partial<SidebarBackendKeys>
): SidebarFrontendVisibility {
	return {
		xRays: featureFlags.xrays ?? false,
		incidents: featureFlags.incidents ?? false,
		tasks: featureFlags.tasks ?? false,
		riskAcceptances: featureFlags.risk_acceptances ?? false,
		securityExceptions: featureFlags.exceptions ?? false,
		followUp: featureFlags.follow_up ?? false,
		ebiosRM: featureFlags.ebiosrm ?? false,
		scoringAssistant: featureFlags.scoring_assistant ?? false,
		vulnerabilities: featureFlags.vulnerabilities ?? false,
		compliance: featureFlags.compliance ?? false,
		thirdPartyCategory: featureFlags.tprm ?? false,
		privacy: featureFlags.privacy ?? false,
		Experimental: featureFlags.experimental ?? false
	};
}

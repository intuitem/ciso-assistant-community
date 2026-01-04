interface FeatureFlagConfig {
	dependsOn?: string[];
	enabled?: boolean;
}

type FeatureFlags = Record<string, FeatureFlagConfig>;

export function loadFeatureFlags() {
	// the name is also the string id
	// the description string should be named 'name'+'ffDescription', we can generate it
	const ff: FeatureFlags = {
		xRays: {},
		incidents: {},
		tasks: {},
		riskAcceptances: {},
		exceptions: {},
		followUp: {},
		ebiosRm: { dependsOn: ['tprm'] },
		scoringAssistant: {},
		vulnerabilities: {},
		compliance: {},
		tprm: {},
		privacy: {},
		experimental: {},
		quantitativeRiskStudies: {}
	};
	return ff;
}

export function loadFeatureFlags() {
	// the name is also the string id
	// the description string should be named 'name'+'ffDescription', we can generate it
	const ff = {
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
		experimental: {}
	};
	return ff;
}

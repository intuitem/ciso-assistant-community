export type FeatureFlag = 'allow_all' | 'risk' | 'compliance' | string;

export const defaultSidebarVisibility = {
	xRays: true,
	incidents: true,
	tasks: true,
	riskAcceptances: true,
	securityExceptions: true,
	followUp: true,
	ebiosRM: true,
	scoringAssistant: true,
	vulnerabilities: true,
	compliance: true,
	thirdPartyCategory: true,
	privacy: true,
	Experimental: true
};

export function getSidebarVisibility(featureFlag: FeatureFlag) {
	switch (featureFlag) {
		case 'allow_all':
			return {
				...defaultSidebarVisibility
			};
		case 'risk':
			return {
				xRays: false,
				incidents: false,
				tasks: false,
				riskAcceptances: true,
				securityExceptions: true,
				followUp: false,
				ebiosRM: true,
				scoringAssistant: true,
				vulnerabilities: true,
				compliance: false,
				thirdPartyCategory: false,
				privacy: false,
				Experimental: true
			};
		case 'compliance':
			return {
				xRays: false,
				incidents: false,
				tasks: false,
				riskAcceptances: false,
				securityExceptions: false,
				followUp: false,
				ebiosRM: false,
				scoringAssistant: false,
				vulnerabilities: false,
				compliance: true,
				thirdPartyCategory: false,
				privacy: false,
				Experimental: true
			};
		default:
			return defaultSidebarVisibility;
	}
}

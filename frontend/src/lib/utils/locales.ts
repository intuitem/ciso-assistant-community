import * as m from '$paraglide/messages';
import type { ModelInfo } from '$lib/utils/types';

export const LOCALE_MAP = {
	en: {
		name: 'english',
		flag: '🇬🇧'
	},
	fr: {
		name: 'french',
		flag: '🇫🇷'
	}
};

export function toCamelCase(str: string) {
	return str.replace(/(?:^\w|[A-Z]|\b\w)/g, function (word, index) {
        return index == 0 ? word.toLowerCase() : word.toUpperCase();
    }).replace(/\s+/g, '');
}

export function getDeterminant(lang: string, defined: string, model: ModelInfo, plural=false): string {
	const determinantTable = {
		"fr": {
			"defined": {
				"plural": "les",
				"m": "le",
				"f": "la"
			},
			"undefined": {
				"plural": "des",
				"m": "un",
				"f": "une"
			}
		}
	};

	if (lang === "en")
		return '';
	else if (lang === "fr" && plural)
		return determinantTable[lang][defined]["plural"];
	else
		return determinantTable[lang][defined][model.localFrGender];
}

interface LocalItems {
	[key: string]: string;
};


export function localItems(languageTag: string): LocalItems {
	const LOCAL_ITEMS = {
		french: m.french({ languageTag: languageTag }),
		english: m.english({ languageTag: languageTag }),
		home: m.home({ languageTag: languageTag }),
		edit: m.edit({ languageTag: languageTag }),
		overview: m.overview({ languageTag: languageTag }),
		context: m.context({ languageTag: languageTag }),
		governance: m.governance({ languageTag: languageTag }),
		risk: m.risk({ languageTag: languageTag }),
		compliance: m.compliance({ languageTag: languageTag }),
		organization: m.organization({ languageTag: languageTag }),
		extra: m.extra({ languageTag: languageTag }),
		analytics: m.analytics({ languageTag: languageTag }),
		calendar: m.calendar({ languageTag: languageTag }),
		threats: m.threats({ languageTag: languageTag }),
		securityFunctions: m.securityFunctions({ languageTag: languageTag }),
		securityMeasures: m.securityMeasures({ languageTag: languageTag }),
		assets: m.assets({ languageTag: languageTag }),
		asset: m.asset({ languageTag: languageTag }),
		policies: m.policies({ languageTag: languageTag }),
		riskMatrices: m.riskMatrices({ languageTag: languageTag }),
		riskAssessments: m.riskAssessments({ languageTag: languageTag }),
		riskScenarios: m.riskScenarios({ languageTag: languageTag }),
		riskScenario: m.riskScenario({ languageTag: languageTag }),
		riskAcceptances: m.riskAcceptances({ languageTag: languageTag }),
		riskAcceptance: m.riskAcceptance({ languageTag: languageTag }),
		complianceAssessments: m.complianceAssessments({ languageTag: languageTag }),
		complianceAssessment: m.complianceAssessment({ languageTag: languageTag }),
		evidences: m.evidences({ languageTag: languageTag }),
		evidence: m.evidence({ languageTag: languageTag }),
		frameworks: m.frameworks({ languageTag: languageTag }),
		domains: m.domains({ languageTag: languageTag }),
		projects: m.projects({ languageTag: languageTag }),
		users: m.users({ languageTag: languageTag }),
		user: m.user({ languageTag: languageTag }),
		userGroups: m.userGroups({ languageTag: languageTag }),
		roleAssignments: m.roleAssignments({ languageTag: languageTag }),
		xRays: m.xRays({ languageTag: languageTag }),
		scoringAssistant: m.scoringAssistant({ languageTag: languageTag }),
		libraries: m.libraries({ languageTag: languageTag }),
		backupRestore: m.backupRestore({ languageTag: languageTag }),
		myProfile: m.myProfile({ languageTag: languageTag }),
		aboutCiso: m.aboutCiso({ languageTag: languageTag }),
		Logout: m.Logout({ languageTag: languageTag }),
		name: m.name({ languageTag: languageTag }),
		description: m.description({ languageTag: languageTag }),
		parentDomain: m.parentDomain({ languageTag: languageTag }),
		ref: m.ref({ languageTag: languageTag }),
		refId: m.refId({ languageTag: languageTag }),
		businessValue: m.businessValue({ languageTag: languageTag }),
		email: m.email({ languageTag: languageTag }),
		firstName: m.firstName({ languageTag: languageTag }),
		lastName: m.lastName({ languageTag: languageTag }),
		category: m.category({ languageTag: languageTag }),
		eta: m.eta({ languageTag: languageTag }),
		securityFunction: m.securityFunction({ languageTag: languageTag }),
		securityMeasure: m.securityMeasure({ languageTag: languageTag }),
		provider: m.provider({ languageTag: languageTag }),
		domain: m.domain({ languageTag: languageTag }),
		urn: m.urn({ languageTag: languageTag }),
		id: m.id({ languageTag: languageTag }),
		treatmentStatus: m.treatmentStatus({ languageTag: languageTag }),
		currentLevel: m.currentLevel({ languageTag: languageTag }),
		residualLevel: m.residualLevel({ languageTag: languageTag }),
		riskMatrix: m.riskMatrix({ languageTag: languageTag }),
		project: m.project({ languageTag: languageTag }),
		folder: m.folder({ languageTag: languageTag }),
		riskAssessment: m.riskAssessment({ languageTag: languageTag }),
		threat: m.threat({ languageTag: languageTag }),
		framework: m.framework({ languageTag: languageTag }),
		file: m.file({ languageTag: languageTag }),
		language: m.language({ languageTag: languageTag }),
		builtin: m.builtin({ languageTag: languageTag }),
		status: m.status({ languageTag: languageTag }),
		effort: m.effort({ languageTag: languageTag }),
		impact: m.impact({ languageTag: languageTag }),
		expiryDate: m.expiryDate({ languageTag: languageTag }),
		link: m.link({ languageTag: languageTag }),
		createdAt: m.createdAt({ languageTag: languageTag }),
		updatedAt: m.updatedAt({ languageTag: languageTag }),
		acceptedAt: m.acceptedAt({ languageTag: languageTag }),
		rejectedAt: m.rejectedAt({ languageTag: languageTag }),
		revokedAt: m.revokedAt({ languageTag: languageTag }),
		locale: m.locale({ languageTag: languageTag }),
		defaultLocale: m.defaultLocale({ languageTag: languageTag }),
		annotation: m.annotation({ languageTag: languageTag }),
		library: m.library({ languageTag: languageTag }),
		typicalEvidence: m.typicalEvidence({ languageTag: languageTag }),
		parentAsset: m.parentAsset({ languageTag: languageTag }),
		parentAssets: m.parentAssets({ languageTag: languageTag }),
		approver: m.approver({ languageTag: languageTag }),
		state: m.state({ languageTag: languageTag }),
		justification: m.justification({ languageTag: languageTag }),
		parentFolder: m.parentFolder({ languageTag: languageTag }),
		contentType: m.contentType({ languageTag: languageTag }),
		lcStatus: m.lcStatus({ languageTag: languageTag }),
		internalReference: m.internalReference({ languageTag: languageTag }),
		isActive: m.isActive({ languageTag: languageTag }),
		dateJoined: m.dateJoined({ languageTag: languageTag }),
		version: m.version({ languageTag: languageTag }),
		treatment: m.treatment({ languageTag: languageTag }),
		currentProba: m.currentProba({ languageTag: languageTag }),
		currentImpact: m.currentImpact({ languageTag: languageTag }),
		residualProba: m.residualProba({ languageTag: languageTag }),
		residualImpact: m.residualImpact({ languageTag: languageTag }),
		existingMeasures: m.existingMeasures({ languageTag: languageTag }),
		strengthOfKnowledge: m.strengthOfKnowledge({ languageTag: languageTag }),
		dueDate: m.dueDate({ languageTag: languageTag }),
		attachment: m.attachment({ languageTag: languageTag }),
		observation: m.observation({ languageTag: languageTag }),
		veryLow: m.veryLow({ languageTag: languageTag }),
		low: m.low({ languageTag: languageTag }),
		medium: m.medium({ languageTag: languageTag }),
		high: m.high({ languageTag: languageTag }),
		veryHigh: m.veryHigh({ languageTag: languageTag }),
		planned: m.planned({ languageTag: languageTag }),
		active: m.active({ languageTag: languageTag }),
		inactive: m.inactive({ languageTag: languageTag }),
	};
	return LOCAL_ITEMS;
}
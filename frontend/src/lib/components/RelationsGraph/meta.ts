/** Visual identity per model: colour carries the type, shape carries a second cut
 *  (diamond = asset-like, roundRect = assessment-like, rect = artefact). */
import { m } from '$paraglide/messages';

export interface NodeMeta {
	label: string;
	color: string;
	icon: string;
	symbol: string;
}

interface NodeStyle extends Omit<NodeMeta, 'label'> {
	label: () => string;
}

const FALLBACK: NodeStyle = {
	label: () => m.object(),
	color: '#94a3b8',
	icon: 'fa-circle',
	symbol: 'circle'
};

export const NODE_META: Record<string, NodeStyle> = {
	'applied-controls': {
		label: () => m.appliedControl(),
		color: '#3b82f6',
		icon: 'fa-fire-extinguisher',
		symbol: 'circle'
	},
	'reference-controls': {
		label: () => m.referenceControl(),
		color: '#1e3a8a',
		icon: 'fa-book',
		symbol: 'roundRect'
	},
	'risk-scenarios': {
		label: () => m.riskScenario(),
		color: '#ef4444',
		icon: 'fa-biohazard',
		symbol: 'circle'
	},
	'risk-assessments': {
		label: () => m.riskAssessment(),
		color: '#9f1239',
		icon: 'fa-chart-simple',
		symbol: 'roundRect'
	},
	assets: { label: () => m.asset(), color: '#10b981', icon: 'fa-gem', symbol: 'diamond' },
	'asset-classes': {
		label: () => m.assetClass(),
		color: '#047857',
		icon: 'fa-sitemap',
		symbol: 'roundRect'
	},
	solutions: { label: () => m.solution(), color: '#0d9488', icon: 'fa-cubes', symbol: 'diamond' },
	threats: { label: () => m.threat(), color: '#6d28d9', icon: 'fa-virus', symbol: 'triangle' },
	vulnerabilities: {
		label: () => m.vulnerability(),
		color: '#ec4899',
		icon: 'fa-bug',
		symbol: 'triangle'
	},
	'requirement-assessments': {
		label: () => m.requirement(),
		color: '#f59e0b',
		icon: 'fa-list-check',
		symbol: 'roundRect'
	},
	'compliance-assessments': {
		label: () => m.audit(),
		color: '#b45309',
		icon: 'fa-certificate',
		symbol: 'roundRect'
	},
	'managed-documents': {
		label: () => m.documentVersion(),
		color: '#0284c7',
		icon: 'fa-file-lines',
		symbol: 'rect'
	},
	'classification-levels': {
		label: () => m.classification(),
		color: '#7c2d12',
		icon: 'fa-tag',
		symbol: 'roundRect'
	},
	policies: { label: () => m.policy(), color: '#1d4ed8', icon: 'fa-scroll', symbol: 'rect' },
	processings: {
		label: () => m.processing(),
		color: '#9333ea',
		icon: 'fa-gears',
		symbol: 'roundRect'
	},
	'document-containers': {
		label: () => m.document(),
		color: '#0369a1',
		icon: 'fa-file-contract',
		symbol: 'rect'
	},
	evidences: { label: () => m.evidence(), color: '#06b6d4', icon: 'fa-file-lines', symbol: 'rect' },
	findings: {
		label: () => m.finding(),
		color: '#f97316',
		icon: 'fa-magnifying-glass',
		symbol: 'circle'
	},
	'findings-assessments': {
		label: () => m.followUp(),
		color: '#c2410c',
		icon: 'fa-clipboard-check',
		symbol: 'roundRect'
	},
	'task-templates': {
		label: () => m.taskTemplate(),
		color: '#84cc16',
		icon: 'fa-list-check',
		symbol: 'rect'
	},
	actors: { label: () => m.actor(), color: '#6b7280', icon: 'fa-user', symbol: 'circle' },
	'security-exceptions': {
		label: () => m.securityException(),
		color: '#d946ef',
		icon: 'fa-shield-halved',
		symbol: 'rect'
	},
	incidents: { label: () => m.incident(), color: '#be123c', icon: 'fa-bolt', symbol: 'circle' },
	'organisation-objectives': {
		label: () => m.objective(),
		color: '#0891b2',
		icon: 'fa-bullseye',
		symbol: 'roundRect'
	},
	'operational-scenarios': {
		label: () => m.operationalScenario(),
		color: '#7c3aed',
		icon: 'fa-route',
		symbol: 'roundRect'
	},
	'personal-data': {
		label: () => m.personalData(),
		color: '#db2777',
		icon: 'fa-id-card',
		symbol: 'rect'
	},
	'asset-assessments': {
		label: () => m.assetAssessment(),
		color: '#0f766e',
		icon: 'fa-heart-pulse',
		symbol: 'roundRect'
	},
	'quantitative-risk-scenarios': {
		label: () => m.quantitativeRiskScenario(),
		color: '#7f1d1d',
		icon: 'fa-calculator',
		symbol: 'roundRect'
	},
	'ebios-rm': {
		label: () => m.ebiosRmStudy(),
		color: '#4c1d95',
		icon: 'fa-shield-virus',
		symbol: 'roundRect'
	},
	perimeters: {
		label: () => m.perimeter(),
		color: '#94a3b8',
		icon: 'fa-draw-polygon',
		symbol: 'roundRect'
	},
	folders: { label: () => m.domain(), color: '#94a3b8', icon: 'fa-folder', symbol: 'roundRect' }
};

export function metaFor(urlModel: string): NodeMeta {
	// Resolved per call, not at module load: the label must follow the active locale.
	const style = NODE_META[urlModel] ?? FALLBACK;
	return { ...style, label: style.label() };
}

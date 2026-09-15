/** Visual identity per model: colour carries the type, shape carries a second cut
 *  (diamond = asset-like, roundRect = assessment-like, rect = artefact). */
export interface NodeMeta {
	label: string;
	color: string;
	icon: string;
	symbol: string;
}

const FALLBACK: NodeMeta = {
	label: 'Object',
	color: '#94a3b8',
	icon: 'fa-circle',
	symbol: 'circle'
};

export const NODE_META: Record<string, NodeMeta> = {
	'applied-controls': {
		label: 'Applied control',
		color: '#3b82f6',
		icon: 'fa-fire-extinguisher',
		symbol: 'circle'
	},
	'reference-controls': {
		label: 'Reference control',
		color: '#1e3a8a',
		icon: 'fa-book',
		symbol: 'roundRect'
	},
	'risk-scenarios': {
		label: 'Risk scenario',
		color: '#ef4444',
		icon: 'fa-biohazard',
		symbol: 'circle'
	},
	'risk-assessments': {
		label: 'Risk assessment',
		color: '#9f1239',
		icon: 'fa-chart-simple',
		symbol: 'roundRect'
	},
	assets: { label: 'Asset', color: '#10b981', icon: 'fa-gem', symbol: 'diamond' },
	'asset-classes': {
		label: 'Asset class',
		color: '#047857',
		icon: 'fa-sitemap',
		symbol: 'roundRect'
	},
	solutions: { label: 'Solution', color: '#0d9488', icon: 'fa-cubes', symbol: 'diamond' },
	threats: { label: 'Threat', color: '#6d28d9', icon: 'fa-virus', symbol: 'triangle' },
	vulnerabilities: { label: 'Vulnerability', color: '#ec4899', icon: 'fa-bug', symbol: 'triangle' },
	'requirement-assessments': {
		label: 'Requirement',
		color: '#f59e0b',
		icon: 'fa-list-check',
		symbol: 'roundRect'
	},
	'compliance-assessments': {
		label: 'Audit',
		color: '#b45309',
		icon: 'fa-certificate',
		symbol: 'roundRect'
	},
	'document-containers': {
		label: 'Document',
		color: '#0369a1',
		icon: 'fa-file-contract',
		symbol: 'rect'
	},
	evidences: { label: 'Evidence', color: '#06b6d4', icon: 'fa-file-lines', symbol: 'rect' },
	findings: { label: 'Finding', color: '#f97316', icon: 'fa-magnifying-glass', symbol: 'circle' },
	'findings-assessments': {
		label: 'Follow-up',
		color: '#c2410c',
		icon: 'fa-clipboard-check',
		symbol: 'roundRect'
	},
	'task-templates': { label: 'Task', color: '#84cc16', icon: 'fa-list-check', symbol: 'rect' },
	actors: { label: 'Actor', color: '#6b7280', icon: 'fa-user', symbol: 'circle' },
	'security-exceptions': {
		label: 'Security exception',
		color: '#d946ef',
		icon: 'fa-shield-halved',
		symbol: 'rect'
	},
	incidents: { label: 'Incident', color: '#be123c', icon: 'fa-bolt', symbol: 'circle' },
	'organisation-objectives': {
		label: 'Objective',
		color: '#0891b2',
		icon: 'fa-bullseye',
		symbol: 'roundRect'
	},
	'operational-scenarios': {
		label: 'Operational scenario',
		color: '#7c3aed',
		icon: 'fa-route',
		symbol: 'roundRect'
	},
	'personal-data': { label: 'Personal data', color: '#db2777', icon: 'fa-id-card', symbol: 'rect' },
	'asset-assessments': { label: 'Asset assessment', color: '#0f766e', icon: 'fa-heart-pulse', symbol: 'roundRect' },
	'quantitative-risk-scenarios': { label: 'Quantitative scenario', color: '#7f1d1d', icon: 'fa-calculator', symbol: 'roundRect' },
	'ebios-rm': { label: 'EBIOS RM study', color: '#4c1d95', icon: 'fa-shield-virus', symbol: 'roundRect' },
	perimeters: {
		label: 'Perimeter',
		color: '#94a3b8',
		icon: 'fa-draw-polygon',
		symbol: 'roundRect'
	},
	folders: { label: 'Domain', color: '#94a3b8', icon: 'fa-folder', symbol: 'roundRect' }
};

export function metaFor(urlModel: string): NodeMeta {
	return NODE_META[urlModel] ?? FALLBACK;
}

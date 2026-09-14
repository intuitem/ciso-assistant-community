/**
 * Fake GRC universe for the mini-graph prototype. No backend: the whole point is
 * to settle the interaction model (depth, fan-out caps, re-rooting) before
 * deciding what `GET /{model}/{id}/neighborhood/` should return.
 */

export type NodeType =
	| 'applied-control'
	| 'risk-scenario'
	| 'asset'
	| 'threat'
	| 'vulnerability'
	| 'requirement-assessment'
	| 'compliance-assessment'
	| 'risk-assessment'
	| 'evidence'
	| 'finding'
	| 'finding-assessment'
	| 'task'
	| 'actor'
	| 'reference-control'
	| 'security-exception'
	| 'incident'
	| 'perimeter'
	| 'folder';

export interface UniverseNode {
	id: string;
	type: NodeType;
	name: string;
	/** Shown in the hover card. Deliberately few: a mini graph is not a detail view. */
	meta?: Record<string, string>;
}

export interface UniverseEdge {
	source: string;
	target: string;
	/** Relation label, following the product-docs verb convention. */
	verb: string;
}

export const TYPE_META: Record<
	NodeType,
	{ label: string; color: string; icon: string; symbol: string }
> = {
	'applied-control': {
		label: 'Applied control',
		color: '#3b82f6',
		icon: 'fa-fire-extinguisher',
		symbol: 'circle'
	},
	'risk-scenario': {
		label: 'Risk scenario',
		color: '#ef4444',
		icon: 'fa-biohazard',
		symbol: 'circle'
	},
	asset: { label: 'Asset', color: '#10b981', icon: 'fa-gem', symbol: 'diamond' },
	threat: { label: 'Threat', color: '#6d28d9', icon: 'fa-virus', symbol: 'triangle' },
	vulnerability: { label: 'Vulnerability', color: '#ec4899', icon: 'fa-bug', symbol: 'triangle' },
	'requirement-assessment': {
		label: 'Requirement',
		color: '#f59e0b',
		icon: 'fa-list-check',
		symbol: 'roundRect'
	},
	'compliance-assessment': {
		label: 'Audit',
		color: '#b45309',
		icon: 'fa-certificate',
		symbol: 'roundRect'
	},
	'risk-assessment': {
		label: 'Risk assessment',
		color: '#9f1239',
		icon: 'fa-chart-simple',
		symbol: 'roundRect'
	},
	evidence: { label: 'Evidence', color: '#06b6d4', icon: 'fa-file-lines', symbol: 'rect' },
	finding: { label: 'Finding', color: '#f97316', icon: 'fa-magnifying-glass', symbol: 'circle' },
	'finding-assessment': {
		label: 'Follow-up',
		color: '#c2410c',
		icon: 'fa-clipboard-check',
		symbol: 'roundRect'
	},
	task: { label: 'Task', color: '#84cc16', icon: 'fa-list-check', symbol: 'rect' },
	actor: { label: 'Actor', color: '#6b7280', icon: 'fa-user', symbol: 'circle' },
	'reference-control': {
		label: 'Reference control',
		color: '#1e3a8a',
		icon: 'fa-book',
		symbol: 'roundRect'
	},
	'security-exception': {
		label: 'Security exception',
		color: '#d946ef',
		icon: 'fa-shield-halved',
		symbol: 'rect'
	},
	incident: { label: 'Incident', color: '#be123c', icon: 'fa-bolt', symbol: 'circle' },
	perimeter: { label: 'Perimeter', color: '#94a3b8', icon: 'fa-draw-polygon', symbol: 'roundRect' },
	folder: { label: 'Domain', color: '#cbd5e1', icon: 'fa-folder', symbol: 'roundRect' }
};

export const NODES: UniverseNode[] = [
	// controls
	{
		id: 'ac-fde',
		type: 'applied-control',
		name: 'Full-disk encryption on endpoints',
		meta: { ref: 'M.12', status: 'Active', priority: 'P1', effort: 'Medium' }
	},
	{
		id: 'ac-mdm',
		type: 'applied-control',
		name: 'MDM enrolment & compliance baseline',
		meta: { ref: 'M.14', status: 'In progress', priority: 'P2' }
	},
	{
		id: 'ac-wipe',
		type: 'applied-control',
		name: 'Remote wipe capability',
		meta: { ref: 'M.15', status: 'Active' }
	},
	{
		id: 'ac-locks',
		type: 'applied-control',
		name: 'Cable locks in open offices',
		meta: { ref: 'M.03', status: 'Active' }
	},
	{
		id: 'ac-dlp',
		type: 'applied-control',
		name: 'DLP on egress gateways',
		meta: { ref: 'M.21', status: 'To do', priority: 'P1' }
	},
	{
		id: 'ac-backup',
		type: 'applied-control',
		name: 'Encrypted offsite backups',
		meta: { ref: 'M.08', status: 'Active' }
	},
	{
		id: 'ac-awareness',
		type: 'applied-control',
		name: 'Security awareness training',
		meta: { ref: 'M.01', status: 'Active' }
	},
	{
		id: 'ac-mfa',
		type: 'applied-control',
		name: 'MFA on remote access',
		meta: { ref: 'M.05', status: 'In progress' }
	},

	// assets
	{
		id: 'as-laptops',
		type: 'asset',
		name: 'Field laptops',
		meta: { ref: 'A.7', type: 'Support', class: 'Endpoint' }
	},
	{
		id: 'as-custdb',
		type: 'asset',
		name: 'Customer database',
		meta: { ref: 'A.1', type: 'Primary', class: 'Data' }
	},
	{
		id: 'as-crm',
		type: 'asset',
		name: 'CRM SaaS',
		meta: { ref: 'A.12', type: 'Support', class: 'Application' }
	},
	{
		id: 'as-payroll',
		type: 'asset',
		name: 'Payroll data',
		meta: { ref: 'A.2', type: 'Primary', class: 'Data' }
	},

	// reference controls
	{
		id: 'rc-crypto',
		type: 'reference-control',
		name: 'A.8.24 Use of cryptography',
		meta: { ref: 'A.8.24', library: 'ISO/IEC 27001:2022', category: 'Technical' }
	},
	{
		id: 'rc-mobile',
		type: 'reference-control',
		name: 'A.8.1 User endpoint devices',
		meta: { ref: 'A.8.1', library: 'ISO/IEC 27001:2022' }
	},

	// evidence
	{
		id: 'ev-fde-report',
		type: 'evidence',
		name: 'FDE coverage report 2026-Q2',
		meta: { ref: 'EV.03', revisions: '3', updated: '2026-07-02' }
	},
	{
		id: 'ev-gpo',
		type: 'evidence',
		name: 'BitLocker GPO export',
		meta: { ref: 'EV.04', revisions: '1', updated: '2026-04-18' }
	},
	{
		id: 'ev-mdm-screens',
		type: 'evidence',
		name: 'MDM compliance screenshots',
		meta: { ref: 'EV.09', revisions: '2' }
	},

	// actors
	{
		id: 'act-alice',
		type: 'actor',
		name: 'A. Martin',
		meta: { kind: 'User', role: 'IT security lead' }
	},
	{ id: 'act-itops', type: 'actor', name: 'IT Operations', meta: { kind: 'Team' } },

	// compliance
	{
		id: 'ra-8-24',
		type: 'requirement-assessment',
		name: 'A.8.24 Use of cryptography',
		meta: { ref: 'A.8.24', result: 'Compliant', status: 'Done' }
	},
	{
		id: 'ra-8-1',
		type: 'requirement-assessment',
		name: 'A.8.1 User endpoint devices',
		meta: { ref: 'A.8.1', result: 'Partially compliant', status: 'In progress' }
	},
	{
		id: 'ra-cc61',
		type: 'requirement-assessment',
		name: 'CC6.1 Logical access controls',
		meta: { ref: 'CC6.1', result: 'Compliant' }
	},
	{
		id: 'au-iso',
		type: 'compliance-assessment',
		name: 'ISO/IEC 27001:2022 — Group certification',
		meta: { ref: 'ISO 27001', progress: '78%', framework: 'ISO 27001' }
	},
	{
		id: 'au-soc2',
		type: 'compliance-assessment',
		name: 'SOC 2 Type II — Platform',
		meta: { ref: 'SOC 2', progress: '42%', framework: 'SOC 2' }
	},

	// risk
	{
		id: 'rs-theft',
		type: 'risk-scenario',
		name: 'Laptop theft leads to customer data disclosure',
		meta: { ref: 'R.4', current: 'High', residual: 'Medium' }
	},
	{
		id: 'rs-exfil',
		type: 'risk-scenario',
		name: 'Database dump exfiltrated by insider',
		meta: { ref: 'R.7', current: 'Critical', residual: 'High' }
	},
	{
		id: 'rs-phish',
		type: 'risk-scenario',
		name: 'Phishing leads to credential compromise',
		meta: { ref: 'R.1', current: 'High', residual: 'Medium' }
	},
	{
		id: 'rsa-2026',
		type: 'risk-assessment',
		name: '2026 corporate risk review',
		meta: { ref: 'RA.26', matrix: '5x5 balanced', status: 'In progress' }
	},
	{
		id: 'th-theft',
		type: 'threat',
		name: 'Theft of equipment',
		meta: { ref: 'T.05', library: 'ISO 27005' }
	},
	{
		id: 'th-insider',
		type: 'threat',
		name: 'Malicious insider',
		meta: { ref: 'T.11', library: 'ISO 27005' }
	},
	{
		id: 'th-phish',
		type: 'threat',
		name: 'Phishing',
		meta: { library: 'MITRE ATT&CK', ref: 'T1566' }
	},
	{
		id: 'vu-nofde',
		type: 'vulnerability',
		name: 'Legacy fleet without full-disk encryption',
		meta: { ref: 'V.03', severity: 'High', status: 'Confirmed' }
	},
	{
		id: 'vu-weakmfa',
		type: 'vulnerability',
		name: 'MFA not enforced on VPN',
		meta: { ref: 'V.07', severity: 'Critical', status: 'Mitigated' }
	},

	// findings / ops
	{
		id: 'fi-devlaptops',
		type: 'finding',
		name: '12 developer laptops unencrypted',
		meta: { ref: 'F.11', severity: 'High', status: 'Open' }
	},
	{
		id: 'fa-pentest',
		type: 'finding-assessment',
		name: 'Internal pentest 2026-05',
		meta: { ref: 'PT.05', findings: '9' }
	},
	{
		id: 'tk-fde-check',
		type: 'task',
		name: 'Quarterly encryption coverage check',
		meta: { ref: 'TK.02', recurrence: 'Quarterly', next: '2026-10-01' }
	},
	{
		id: 'tk-mdm-review',
		type: 'task',
		name: 'Monthly MDM exception review',
		meta: { ref: 'TK.07', recurrence: 'Monthly' }
	},
	{
		id: 'se-pos',
		type: 'security-exception',
		name: 'Legacy POS terminals — FDE exemption',
		meta: { ref: 'EX.01', status: 'Approved', expires: '2026-12-31' }
	},
	{
		id: 'in-lost',
		type: 'incident',
		name: 'INC-2026-011 — Laptop lost in transit',
		meta: { ref: 'INC-11', severity: 'Major', status: 'Closed' }
	},

	// context
	{ id: 'fo-corp', type: 'folder', name: 'Corporate IT', meta: { kind: 'Domain' } },
	{
		id: 'pe-endpoint',
		type: 'perimeter',
		name: 'Endpoint estate',
		meta: { status: 'In production' }
	}
];

export const EDGES: UniverseEdge[] = [
	// --- around ac-fde ---
	{ source: 'rc-crypto', target: 'ac-fde', verb: 'templates' },
	{ source: 'ac-fde', target: 'as-laptops', verb: 'protects' },
	{ source: 'ac-fde', target: 'as-custdb', verb: 'protects' },
	{ source: 'ac-fde', target: 'ev-fde-report', verb: 'evidenced by' },
	{ source: 'ac-fde', target: 'ev-gpo', verb: 'evidenced by' },
	{ source: 'ac-fde', target: 'act-alice', verb: 'owned by' },
	{ source: 'ra-8-24', target: 'ac-fde', verb: 'satisfied by' },
	{ source: 'ra-cc61', target: 'ac-fde', verb: 'satisfied by' },
	{ source: 'rs-theft', target: 'ac-fde', verb: 'mitigated by' },
	{ source: 'rs-exfil', target: 'ac-fde', verb: 'mitigated by' },
	{ source: 'fi-devlaptops', target: 'ac-fde', verb: 'remediated by' },
	{ source: 'vu-nofde', target: 'ac-fde', verb: 'remediated by' },
	{ source: 'tk-fde-check', target: 'ac-fde', verb: 'maintains' },
	{ source: 'ac-fde', target: 'se-pos', verb: 'excepted by' },
	{ source: 'fo-corp', target: 'ac-fde', verb: 'scopes' },

	// --- around rs-theft ---
	{ source: 'rsa-2026', target: 'rs-theft', verb: 'comprises' },
	{ source: 'rs-theft', target: 'as-laptops', verb: 'targets' },
	{ source: 'rs-theft', target: 'as-custdb', verb: 'targets' },
	{ source: 'rs-theft', target: 'th-theft', verb: 'driven by' },
	{ source: 'rs-theft', target: 'vu-nofde', verb: 'exploits' },
	{ source: 'rs-theft', target: 'ac-mdm', verb: 'mitigated by' },
	{ source: 'rs-theft', target: 'ac-wipe', verb: 'mitigated by' },
	{ source: 'rs-theft', target: 'ac-locks', verb: 'mitigated by' },
	{ source: 'rs-theft', target: 'in-lost', verb: 'realised by' },
	{ source: 'rs-theft', target: 'act-alice', verb: 'owned by' },
	{ source: 'fo-corp', target: 'rs-theft', verb: 'scopes' },

	// --- rest of the world (depth 2-3 material) ---
	{ source: 'au-iso', target: 'ra-8-24', verb: 'comprises' },
	{ source: 'au-iso', target: 'ra-8-1', verb: 'comprises' },
	{ source: 'au-soc2', target: 'ra-cc61', verb: 'comprises' },
	{ source: 'ra-8-1', target: 'ac-mdm', verb: 'satisfied by' },
	{ source: 'ra-8-24', target: 'ac-backup', verb: 'satisfied by' },
	{ source: 'au-iso', target: 'fo-corp', verb: 'scoped by' },
	{ source: 'au-iso', target: 'pe-endpoint', verb: 'narrows' },

	{ source: 'rsa-2026', target: 'rs-exfil', verb: 'comprises' },
	{ source: 'rsa-2026', target: 'rs-phish', verb: 'comprises' },
	{ source: 'rs-exfil', target: 'as-custdb', verb: 'targets' },
	{ source: 'rs-exfil', target: 'th-insider', verb: 'driven by' },
	{ source: 'rs-exfil', target: 'ac-dlp', verb: 'mitigated by' },
	{ source: 'rs-exfil', target: 'ac-backup', verb: 'mitigated by' },
	{ source: 'rs-phish', target: 'rs-exfil', verb: 'precedes' },
	{ source: 'rs-phish', target: 'th-phish', verb: 'driven by' },
	{ source: 'rs-phish', target: 'vu-weakmfa', verb: 'exploits' },
	{ source: 'rs-phish', target: 'ac-awareness', verb: 'mitigated by' },
	{ source: 'rs-phish', target: 'ac-mfa', verb: 'mitigated by' },
	{ source: 'vu-weakmfa', target: 'ac-mfa', verb: 'remediated by' },

	{ source: 'ac-mdm', target: 'rc-mobile', verb: 'templated by' },
	{ source: 'ac-mdm', target: 'ev-mdm-screens', verb: 'evidenced by' },
	{ source: 'ac-mdm', target: 'act-itops', verb: 'owned by' },
	{ source: 'ac-mdm', target: 'as-laptops', verb: 'protects' },
	{ source: 'tk-mdm-review', target: 'ac-mdm', verb: 'maintains' },
	{ source: 'ac-wipe', target: 'as-laptops', verb: 'protects' },
	{ source: 'ac-backup', target: 'as-custdb', verb: 'protects' },
	{ source: 'ac-backup', target: 'as-payroll', verb: 'protects' },
	{ source: 'ac-dlp', target: 'as-custdb', verb: 'protects' },

	{ source: 'fa-pentest', target: 'fi-devlaptops', verb: 'reports' },
	{ source: 'fi-devlaptops', target: 'as-laptops', verb: 'affects' },
	{ source: 'fi-devlaptops', target: 'act-alice', verb: 'owned by' },

	{ source: 'as-custdb', target: 'as-crm', verb: 'depends on' },
	{ source: 'as-laptops', target: 'pe-endpoint', verb: 'sits in' },
	{ source: 'fo-corp', target: 'as-laptops', verb: 'scopes' },
	{ source: 'fo-corp', target: 'as-custdb', verb: 'scopes' },
	{ source: 'fo-corp', target: 'as-payroll', verb: 'scopes' },
	{ source: 'fo-corp', target: 'ac-mdm', verb: 'scopes' },
	{ source: 'fo-corp', target: 'ac-wipe', verb: 'scopes' },
	{ source: 'fo-corp', target: 'ac-dlp', verb: 'scopes' },
	{ source: 'fo-corp', target: 'ac-backup', verb: 'scopes' },
	{ source: 'fo-corp', target: 'ac-awareness', verb: 'scopes' },
	{ source: 'fo-corp', target: 'ac-mfa', verb: 'scopes' },
	{ source: 'fo-corp', target: 'ac-locks', verb: 'scopes' },
	{ source: 'fo-corp', target: 'rsa-2026', verb: 'scopes' },
	{ source: 'fo-corp', target: 'rs-exfil', verb: 'scopes' },
	{ source: 'fo-corp', target: 'rs-phish', verb: 'scopes' }
];

// A real applied control is cited by a dozen requirements across several frameworks.
// The fixture needs that shape, otherwise the fan-out cap never fires and the
// prototype flatters itself.
const CITATIONS: Array<[string, string, string, string]> = [
	['ra-a5-10', 'A.5.10 Acceptable use of information', 'au-iso', 'Compliant'],
	['ra-a5-33', 'A.5.33 Protection of records', 'au-iso', 'Compliant'],
	['ra-a7-10', 'A.7.10 Storage media', 'au-iso', 'Partially compliant'],
	['ra-a8-12', 'A.8.12 Data leakage prevention', 'au-iso', 'Non-compliant'],
	['ra-cc62', 'CC6.2 Credential management', 'au-soc2', 'Compliant'],
	['ra-cc67', 'CC6.7 Data transmission & removal', 'au-soc2', 'Compliant'],
	['ra-nis-8', 'Art. 21.2(h) Cryptography policy', 'au-nis2', 'Partially compliant'],
	['ra-nis-9', 'Art. 21.2(i) Asset management', 'au-nis2', 'In progress']
];

NODES.push({
	id: 'au-nis2',
	type: 'compliance-assessment',
	name: 'NIS 2 — Group readiness',
	meta: { ref: 'NIS 2', progress: '31%', framework: 'NIS 2' }
});
EDGES.push({ source: 'fo-corp', target: 'au-nis2', verb: 'scopes' });

for (const [id, name, audit, result] of CITATIONS) {
	NODES.push({
		id,
		type: 'requirement-assessment',
		name,
		meta: { ref: name.split(' ')[0], result }
	});
	EDGES.push({ source: id, target: 'ac-fde', verb: 'satisfied by' });
	EDGES.push({ source: audit, target: id, verb: 'comprises' });
}

// A real ISO 27001 audit carries ninety-odd requirement assessments. Without them
// the fixture cannot reproduce the case the back-relation rule exists for: walking
// applied control -> requirement -> audit and being buried in the audit's other
// requirements, none of which have anything to do with the control you started on.
for (let i = 0; i < 64; i++) {
	const id = `ra-bulk-${i}`;
	const clause = `A.${5 + (i % 4)}.${20 + i}`;
	NODES.push({
		id,
		type: 'requirement-assessment',
		name: `${clause} Control requirement`,
		meta: { ref: clause, result: i % 3 === 0 ? 'Compliant' : 'In progress' }
	});
	EDGES.push({ source: 'au-iso', target: id, verb: 'comprises' });
}

export const NODE_BY_ID = new Map(NODES.map((n) => [n.id, n]));

export interface Neighbor {
	id: string;
	verb: string;
	/** true when the edge points from the neighbor towards the current node. */
	inbound: boolean;
}

const ADJACENCY = (() => {
	const map = new Map<string, Neighbor[]>();
	const push = (from: string, n: Neighbor) => {
		if (!map.has(from)) map.set(from, []);
		map.get(from)!.push(n);
	};
	for (const e of EDGES) {
		push(e.source, { id: e.target, verb: e.verb, inbound: false });
		push(e.target, { id: e.source, verb: e.verb, inbound: true });
	}
	return map;
})();

export function neighborsOf(id: string): Neighbor[] {
	return ADJACENCY.get(id) ?? [];
}

export function degreeOf(id: string): number {
	return neighborsOf(id).length;
}

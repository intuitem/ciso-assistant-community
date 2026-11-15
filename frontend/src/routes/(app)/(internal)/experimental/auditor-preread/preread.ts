export type Readiness = 'gap' | 'weak' | 'ready' | 'excluded' | 'no_guidance';

export interface Guidance {
	questions: { stage: 1 | 2; text: string }[];
	requests: { label: string; kind: string; fresh_days?: number }[];
	sampling: { size: string; population?: string; method?: string } | null;
	interviewees: string[];
	pitfalls: string[];
}

export interface PrereadItem {
	id: string;
	urn_suffix: string;
	ref_id: string;
	name: string;
	result: string;
	status: string;
	guidance: Guidance | null;
	evidences: {
		id: string;
		name: string | null;
		status: string;
		expiry_date: string | null;
		has_file: boolean;
		updated_at: string | null;
		direct: boolean;
		via_controls: string[];
	}[];
	applied_controls: { id: string; name: string | null; status: string; eta: string | null }[];
	findings: { severity: 'error' | 'warning'; msgid: string; msg: string }[];
	readiness: Readiness;
	reasons: string[];
}

export const PEOPLE: Record<string, string> = {
	top: 'Top management',
	ciso: 'ISMS manager / CISO',
	risk: 'Risk owner',
	auditor: 'Internal auditor',
	hr: 'HR',
	legal: 'Legal / compliance',
	dpo: 'Data protection officer',
	proc: 'Procurement',
	facilities: 'Facilities',
	it_lead: 'Head of IT',
	iam: 'Identity & access admin',
	infra: 'Infrastructure & hosting',
	network: 'Network admin',
	endpoint: 'Workplace & endpoints',
	service_desk: 'Service desk / ITSM',
	sec_ops: 'Security operations',
	dev: 'Engineering lead',
	staff: 'Staff (random)'
};

export const READINESS: Record<Readiness, { label: string; rank: number }> = {
	gap: { label: 'Gap', rank: 0 },
	weak: { label: 'Weak', rank: 1 },
	ready: { label: 'Ready', rank: 2 },
	excluded: { label: 'Excluded', rank: 3 },
	no_guidance: { label: 'No guidance', rank: 4 }
};

export const REASONS: Record<string, string> = {
	nothing_linked: 'No evidence linked',
	non_compliant: 'Assessed as non-compliant',
	quality_error: 'Audit quality check raises an error',
	not_assessed: 'Not assessed yet',
	stale_evidence: 'Newest evidence is older than the freshness window',
	fewer_evidences_than_requests: 'Fewer evidences linked than records requested',
	quality_warning: 'Audit quality check raises a warning'
};

export const SECTIONS = [
	{ key: 'clauses', label: 'Clauses 4-10', test: (s: string) => !s.startsWith('a.') },
	{ key: 'a.5', label: 'A.5 Organizational', test: (s: string) => s.startsWith('a.5.') },
	{ key: 'a.6', label: 'A.6 People', test: (s: string) => s.startsWith('a.6.') },
	{ key: 'a.7', label: 'A.7 Physical', test: (s: string) => s.startsWith('a.7.') },
	{ key: 'a.8', label: 'A.8 Technological', test: (s: string) => s.startsWith('a.8.') }
];

export const sectionOf = (suffix: string) => SECTIONS.find((s) => s.test(suffix)) ?? SECTIONS[0];

export const KINDS: Record<string, { label: string; icon: string }> = {
	document: { label: 'Document', icon: 'fa-solid fa-file-lines' },
	record: { label: 'Record', icon: 'fa-solid fa-clipboard-list' },
	technical: { label: 'Technical export', icon: 'fa-solid fa-terminal' },
	observation: { label: 'Observed on site', icon: 'fa-solid fa-eye' }
};

export const STAGES: Record<number, string> = {
	1: 'Stage 1: documentation review',
	2: 'Stage 2: implementation, tested on samples'
};

/** Older than the widest freshness window this requirement asks for. */
export function isStale(updatedAt: string | null, guidance: Guidance | null, now = Date.now()) {
	const windows = (guidance?.requests ?? []).map((r) => r.fresh_days ?? 0).filter(Boolean);
	if (!updatedAt || !windows.length) return false;
	return now - Date.parse(updatedAt) > Math.max(...windows) * 86_400_000;
}

export interface RequestRow {
	item: PrereadItem;
	label: string;
	kind: string;
	fresh_days?: number;
}

/** Every record requested, worst readiness first, then in standard order. */
export function requestList(items: PrereadItem[]): RequestRow[] {
	return items
		.filter((i) => i.guidance && i.readiness !== 'excluded')
		.flatMap((item) => item.guidance!.requests.map((r) => ({ item, ...r })))
		.sort((a, b) => READINESS[a.item.readiness].rank - READINESS[b.item.readiness].rank);
}

/** Requirements grouped by interviewee, busiest first. */
export function interviewPlan(items: PrereadItem[]): [string, PrereadItem[]][] {
	const groups = new Map<string, PrereadItem[]>();
	for (const item of items) {
		if (item.readiness === 'excluded') continue;
		for (const who of item.guidance?.interviewees ?? []) {
			groups.set(who, [...(groups.get(who) ?? []), item]);
		}
	}
	return [...groups].sort((a, b) => b[1].length - a[1].length);
}

/** Tab-separated, ready to paste into a spreadsheet. */
export function requestListTsv(rows: RequestRow[]): string {
	const head = ['Readiness', 'Ref', 'Requirement', 'Request', 'Kind', 'Max age (days)', 'Owner'];
	const clean = (s: string) => s.replace(/[\t\n]/g, ' ');
	return [
		head,
		...rows.map((r) => [
			READINESS[r.item.readiness].label,
			r.item.ref_id,
			r.item.name,
			r.label,
			r.kind,
			r.fresh_days ? String(r.fresh_days) : '',
			PEOPLE[r.item.guidance?.interviewees[0] ?? ''] ?? ''
		])
	]
		.map((cols) => cols.map(clean).join('\t'))
		.join('\n');
}

export type Readiness = 'gap' | 'weak' | 'ready' | 'excluded' | 'no_guidance';

export interface Guidance {
	questions: { id: string; stage: 1 | 2; text: string }[];
	requests: {
		id: string;
		label: string;
		kind: string;
		fresh_days?: number;
		reference_control?: string;
	}[];
	sampling: {
		min: number;
		max: number;
		unit: string;
		population?: string;
		method?: string;
		note?: string;
	}[];
	interviewees: string[];
	pitfalls: { id: string; text: string }[];
}

export interface FiledEvidence {
	id: string;
	name: string | null;
	updated_at: string | null;
	/** Linked to this requirement, not only to another one asking the same document. */
	here: boolean;
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
	/** Findings raised on this requirement by any audit of the framework (Stage 1, internal). */
	prior_findings: {
		id: string;
		ref_id: string | null;
		name: string;
		severity: number;
		status: string;
		open: boolean;
		source: string | null;
		reported_at: string | null;
	}[];
	/** Request id -> evidences matched through its reference control, newest first. */
	filed: Record<string, FiledEvidence[]>;
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
	open_finding: 'Open finding from an earlier audit, potential nonconformity',
	open_minor_finding: 'Open point to watch from an earlier audit',
	nothing_linked: 'No evidence linked',
	non_compliant: 'Assessed as non-compliant',
	quality_error: 'Audit quality check raises an error',
	not_assessed: 'Not assessed yet',
	stale_evidence: 'A requested record is older than its freshness window',
	request_not_on_file: 'A requested document or record is not on file',
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

export const tooOld = (updatedAt: string | null, days: number, now = Date.now()) =>
	!!updatedAt && now - Date.parse(updatedAt) > days * 86_400_000;

/** Unpaired evidence against the tightest window of the requests that cannot be paired. */
export function isStale(updatedAt: string | null, guidance: Guidance | null, now = Date.now()) {
	const windows = (guidance?.requests ?? [])
		.filter((r) => !r.reference_control)
		.map((r) => r.fresh_days ?? 0)
		.filter(Boolean);
	return windows.length > 0 && tooOld(updatedAt, Math.min(...windows), now);
}

export interface RequestRow {
	/** Every requirement asking for it; one row per document, however many ask. */
	items: PrereadItem[];
	id: string;
	label: string;
	kind: string;
	fresh_days?: number;
	reference_control?: string;
	/** Matched evidences, or null when the request cannot be matched automatically. */
	filed: FiledEvidence[] | null;
}

const rank = (i: PrereadItem) => READINESS[i.readiness].rank;
/** The requirement in the worst state among those asking for this record. */
export const worstOf = (row: RequestRow) => row.items.reduce((a, i) => (rank(i) < rank(a) ? i : a));

/** Every record requested once, worst readiness first, then in standard order. */
export function requestList(items: PrereadItem[]): RequestRow[] {
	const rows = new Map<string, RequestRow>();
	for (const item of items.filter((i) => i.guidance && i.readiness !== 'excluded')) {
		for (const r of item.guidance!.requests) {
			const key = r.reference_control ?? `${item.id}:${r.id}`;
			const row = rows.get(key);
			if (!row) {
				rows.set(key, {
					items: [item],
					...r,
					filed: r.reference_control ? (item.filed?.[r.id] ?? []) : null
				});
			} else {
				if (!row.items.includes(item)) row.items.push(item);
				// The tightest cadence any requirement asks for is the one to meet.
				if (r.fresh_days && (!row.fresh_days || r.fresh_days < row.fresh_days))
					row.fresh_days = r.fresh_days;
			}
		}
	}
	return [...rows.values()].sort((a, b) => rank(worstOf(a)) - rank(worstOf(b)));
}

export interface Session {
	id: string;
	label: string;
	members: string[];
	requests?: Guidance['requests'];
	pitfalls?: Guidance['pitfalls'];
}

/** Stage 2 sessions in running order, each with its requirements and the people it needs. */
export function sessionPlan(items: PrereadItem[], sessions: Session[]) {
	const bySuffix = new Map(items.map((i) => [i.urn_suffix, i]));
	return sessions
		.map((session) => {
			const reqs = session.members.flatMap((m) => bySuffix.get(m) ?? []);
			const people = [...new Set(reqs.flatMap((r) => r.guidance?.interviewees ?? []))];
			return { session, reqs, people };
		})
		.filter((s) => s.reqs.length || s.session.requests?.length);
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
	const head = [
		'Readiness',
		'Ref',
		'Requirement',
		'Request',
		'Kind',
		'Max age (days)',
		'Owner',
		'On file'
	];
	const clean = (s: string) => s.replace(/[\t\n]/g, ' ');
	return [
		head,
		...rows.map((r) => [
			READINESS[worstOf(r).readiness].label,
			r.items.map((i) => i.ref_id).join(', '),
			r.items.map((i) => i.name).join('; '),
			r.label,
			r.kind,
			r.fresh_days ? String(r.fresh_days) : '',
			PEOPLE[r.items[0].guidance?.interviewees[0] ?? ''] ?? '',
			r.filed === null
				? ''
				: r.filed.length
					? r.filed.map((e) => e.name ?? '').join('; ')
					: 'missing'
		])
	]
		.map((cols) => cols.map(clean).join('\t'))
		.join('\n');
}

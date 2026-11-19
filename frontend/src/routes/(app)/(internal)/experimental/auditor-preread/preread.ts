import { m } from '#paraglide/messages.js';

/** Labels read in the current locale each time they are shown, not once at import. */
const lazy = (messages: Record<string, () => string>): Record<string, string> =>
	Object.defineProperties(
		{},
		Object.fromEntries(
			Object.entries(messages).map(([k, f]) => [k, { get: () => f(), enumerable: true }])
		)
	);

export type Readiness = 'gap' | 'weak' | 'to_confirm' | 'ready' | 'excluded' | 'no_guidance';

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
	/** Holds a file or a link in its latest revision. */
	has_file: boolean;
	updated_at: string | null;
	/** Linked to this requirement, not only to another one asking the same document. */
	here: boolean;
	/** Paired by hand rather than through the request's reference control. */
	manual: boolean;
}

export interface PrereadItem {
	id: string;
	urn_suffix: string;
	/** Guide entry this requirement maps to; differs from urn_suffix on a projected framework. */
	guide_key: string | null;
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

export const PEOPLE: Record<string, string> = lazy({
	top: m.prereadRoleTop,
	ciso: m.prereadRoleCiso,
	risk: m.prereadRoleRisk,
	auditor: m.prereadRoleAuditor,
	hr: m.prereadRoleHr,
	legal: m.prereadRoleLegal,
	dpo: m.prereadRoleDpo,
	proc: m.prereadRoleProc,
	facilities: m.prereadRoleFacilities,
	it_lead: m.prereadRoleItLead,
	iam: m.prereadRoleIam,
	infra: m.prereadRoleInfra,
	network: m.prereadRoleNetwork,
	endpoint: m.prereadRoleEndpoint,
	service_desk: m.prereadRoleServiceDesk,
	sec_ops: m.prereadRoleSecOps,
	dev: m.prereadRoleDev,
	staff: m.prereadRoleStaff
});

export const READINESS: Record<Readiness, { label: string; rank: number }> = {
	gap: {
		get label() {
			return m.prereadGap();
		},
		rank: 0
	},
	weak: {
		get label() {
			return m.prereadWeak();
		},
		rank: 1
	},
	to_confirm: {
		get label() {
			return m.prereadToConfirm();
		},
		rank: 2
	},
	ready: {
		get label() {
			return m.prereadReady();
		},
		rank: 3
	},
	excluded: {
		get label() {
			return m.prereadExcluded();
		},
		rank: 4
	},
	no_guidance: {
		get label() {
			return m.prereadNoGuidance();
		},
		rank: 5
	}
};

export const REASONS: Record<string, string> = lazy({
	open_finding: m.prereadReasonOpenFinding,
	open_minor_finding: m.prereadReasonOpenMinorFinding,
	nothing_linked: m.prereadReasonNothingLinked,
	non_compliant: m.prereadReasonNonCompliant,
	quality_error: m.prereadReasonQualityError,
	not_assessed: m.prereadReasonNotAssessed,
	stale_evidence: m.prereadReasonStaleEvidence,
	request_not_on_file: m.prereadReasonRequestNotOnFile,
	evidence_to_confirm: m.prereadReasonEvidenceToConfirm,
	quality_warning: m.prereadReasonQualityWarning,
	missing_file: m.prereadReasonMissingFile
});

export const SECTIONS = [
	{
		key: 'clauses',
		get label() {
			return m.prereadSectionClauses();
		},
		test: (s: string) => /^\d/.test(s)
	},
	{
		key: 'a.5',
		get label() {
			return m.prereadSectionA5();
		},
		test: (s: string) => s.startsWith('a.5.')
	},
	{
		key: 'a.6',
		get label() {
			return m.prereadSectionA6();
		},
		test: (s: string) => s.startsWith('a.6.')
	},
	{
		key: 'a.7',
		get label() {
			return m.prereadSectionA7();
		},
		test: (s: string) => s.startsWith('a.7.')
	},
	{
		key: 'a.8',
		get label() {
			return m.prereadSectionA8();
		},
		test: (s: string) => s.startsWith('a.8.')
	},
	{
		// Requirements of a projected framework with no ISO number of their own.
		key: 'other',
		get label() {
			return m.prereadSectionOther();
		},
		test: (s: string): boolean => !SECTIONS.slice(0, -1).some((x) => x.test(s))
	}
];

/** The guide entry an item answers to, for grouping by section or session. */
export const keyOf = (i: PrereadItem) => i.guide_key ?? i.urn_suffix;

export const sectionOf = (suffix: string) => SECTIONS.find((s) => s.test(suffix)) ?? SECTIONS[0];

export const KINDS: Record<string, { label: string; icon: string }> = {
	document: {
		get label() {
			return m.prereadKindDocument();
		},
		icon: 'fa-solid fa-file-lines'
	},
	record: {
		get label() {
			return m.prereadKindRecord();
		},
		icon: 'fa-solid fa-clipboard-list'
	},
	technical: {
		get label() {
			return m.prereadKindTechnical();
		},
		icon: 'fa-solid fa-terminal'
	},
	observation: {
		get label() {
			return m.prereadKindObservation();
		},
		icon: 'fa-solid fa-eye'
	}
};

export const STAGES: Record<number, string> = lazy({
	1: m.prereadStage1Long,
	2: m.prereadStage2Long
});

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
	/** Nothing paired, but a requirement asking for it holds evidence that may answer it. */
	toConfirm: boolean;
}

/** Evidence linked to the requirement that no request is paired with yet. */
export const unpairedOf = (i: PrereadItem) => {
	const paired = new Set(Object.values(i.filed ?? {}).flatMap((f) => f.map((e) => e.id)));
	return i.evidences.filter((e) => !paired.has(e.id));
};

const rank = (i: PrereadItem) => READINESS[i.readiness].rank;
/** The requirement in the worst state among those asking for this record. */
export const worstOf = (row: RequestRow) => row.items.reduce((a, i) => (rank(i) < rank(a) ? i : a));

/** Every record requested once, worst readiness first, then in standard order. */
export function requestList(items: PrereadItem[]): RequestRow[] {
	const rows = new Map<string, RequestRow>();
	for (const item of items.filter((i) => i.guidance && i.readiness !== 'excluded')) {
		for (const r of item.guidance!.requests) {
			const key = r.reference_control ?? `${keyOf(item)}:${r.id}`;
			const row = rows.get(key);
			if (!row) {
				rows.set(key, {
					items: [item],
					...r,
					filed: r.reference_control || item.filed?.[r.id] ? (item.filed?.[r.id] ?? []) : null,
					toConfirm: false
				});
			} else {
				if (!row.items.includes(item)) row.items.push(item);
				// The tightest cadence any requirement asks for is the one to meet.
				if (r.fresh_days && (!row.fresh_days || r.fresh_days < row.fresh_days))
					row.fresh_days = r.fresh_days;
			}
		}
	}
	for (const row of rows.values())
		row.toConfirm =
			row.kind !== 'observation' &&
			!row.filed?.length &&
			row.items.some((i) => unpairedOf(i).length);
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
	// Several requirements of a projected framework can share one entry (4.2 a, 4.2 b).
	const byKey = new Map<string, PrereadItem[]>();
	for (const i of items) byKey.set(keyOf(i), [...(byKey.get(keyOf(i)) ?? []), i]);
	return sessions
		.map((session) => {
			const reqs = session.members.flatMap((m) => byKey.get(m) ?? []);
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
		m.prereadColReadiness(),
		m.prereadColRef(),
		m.prereadColRequirement(),
		m.prereadColRequest(),
		m.prereadColKind(),
		m.prereadColMaxAgeDays(),
		m.prereadColOwner(),
		m.prereadColOnFile()
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
			r.filed?.length
				? r.filed.map((e) => e.name ?? '').join('; ')
				: r.toConfirm
					? m.prereadTsvToConfirm()
					: r.kind === 'observation'
						? ''
						: m.prereadTsvMissing()
		])
	]
		.map((cols) => cols.map(clean).join('\t'))
		.join('\n');
}

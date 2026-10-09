import { compliancePercent } from '$lib/utils/compliance';
import { COUNT, type CountTuple, type DomainTreeFeed } from './feed';

export type Metric = 'compliance' | 'score';
export type Aggregation = 'audits' | 'pooled' | 'children';
export type Audit = DomainTreeFeed['audits'][number];

export interface Stats {
	rows: number;
	compliant: number;
	partial: number;
	nonCompliant: number;
	notApplicable: number;
	notAssessed: number;
	/** Weighted sum of scores rebased to 0..1, and the weights behind it. */
	scoreSum: number;
	scored: number;
	/** The audit page's own score (0..100), used instead when no filter applies. */
	exactScore?: number | null;
}

export interface TreeNode {
	id: string;
	name: string;
	viewable: boolean;
	depth: number;
	parent: TreeNode | null;
	children: TreeNode[];
	audit: Audit | null;
	own: Stats | null;
	branch: Stats;
	auditsInBranch: number;
	descendants: number;
}

/** `section` is a section ref_id; null means no filter. */
export interface Filters {
	ig: string | null;
	section: string | null;
}

export const AGGREGATIONS: { key: Aggregation; label: string; caption: string }[] = [
	{
		key: 'audits',
		label: 'Mean of audits',
		caption: 'mean of the audits in the branch, each audit counts once'
	},
	{
		key: 'pooled',
		label: 'All requirements pooled',
		caption: 'all requirements of the branch counted together, wider scopes weigh more'
	},
	{
		key: 'children',
		label: 'Mean of sub-domains',
		caption: "mean of the domain's own audit and each sub-domain's average, level by level"
	}
];

export function emptyStats(): Stats {
	return {
		rows: 0,
		compliant: 0,
		partial: 0,
		nonCompliant: 0,
		notApplicable: 0,
		notAssessed: 0,
		scoreSum: 0,
		scored: 0
	};
}

function addTuple(s: Stats, t: CountTuple) {
	s.compliant += t[COUNT.compliant];
	s.partial += t[COUNT.partial];
	s.nonCompliant += t[COUNT.nonCompliant];
	s.notApplicable += t[COUNT.notApplicable];
	s.notAssessed += t[COUNT.notAssessed];
	s.rows +=
		t[COUNT.compliant] +
		t[COUNT.partial] +
		t[COUNT.nonCompliant] +
		t[COUNT.notApplicable] +
		t[COUNT.notAssessed];
	s.scoreSum += t[COUNT.scoreSum];
	s.scored += t[COUNT.scored];
}

const SUMMED = [
	'rows',
	'compliant',
	'partial',
	'nonCompliant',
	'notApplicable',
	'notAssessed',
	'scoreSum',
	'scored'
] as const;

function merge(into: Stats, from: Stats) {
	for (const k of SUMMED) into[k] += from[k];
}

export function assessed(s: Stats) {
	return s.compliant + s.partial + s.nonCompliant;
}

/** 0..100, or null when nothing measurable. */
export function metricValue(s: Stats | null, metric: Metric): number | null {
	if (!s) return null;
	if (metric === 'compliance') return compliancePercent(s.compliant, s.partial, s.nonCompliant);
	if (s.exactScore !== undefined) return s.exactScore;
	return s.scored ? (s.scoreSum / s.scored) * 100 : null;
}

export function progressValue(s: Stats | null): number | null {
	if (!s) return null;
	const d = s.rows - s.notApplicable;
	return d ? (assessed(s) / d) * 100 : null;
}

function tupleFilter(feed: DomainTreeFeed, f: Filters) {
	const section = f.section ? feed.sections.findIndex((s) => s.ref_id === f.section) : -1;
	const sigOk = feed.signatures.map((sig) => !f.ig || sig.includes(f.ig));
	return (sectionIdx: number, sigIdx: number) =>
		sigOk[sigIdx] && (section < 0 || sectionIdx === section);
}

/** Own stats per folder id, for the folders that have an audit. */
export function ownStats(feed: DomainTreeFeed, f: Filters): Map<string, Stats> {
	const match = tupleFilter(feed, f);
	const out = new Map<string, Stats>();
	const unfiltered = !f.ig && !f.section;
	for (const a of feed.audits) {
		if (a.results_hidden) continue;
		const s = emptyStats();
		if (unfiltered) s.exactScore = a.score;
		out.set(a.folder_id, s);
	}
	for (const t of feed.counts) {
		if (!match(t[COUNT.section], t[COUNT.signature])) continue;
		addTuple(out.get(feed.audits[t[COUNT.audit]].folder_id)!, t);
	}
	return out;
}

/** Number of framework requirements in the filtered scope. */
export function scopeSize(feed: DomainTreeFeed, f: Filters): number {
	const match = tupleFilter(feed, f);
	return feed.scope.reduce((n, [s, g, c]) => (match(s, g) ? n + c : n), 0);
}

export function buildTree(feed: DomainTreeFeed, f: Filters): TreeNode | null {
	const auditByFolder = new Map(feed.audits.map((a) => [a.folder_id, a]));
	const own = ownStats(feed, f);
	const nodes = new Map<string, TreeNode>();
	for (const folder of feed.folders) {
		const audit = auditByFolder.get(folder.id) ?? null;
		nodes.set(folder.id, {
			id: folder.id,
			name: folder.name,
			viewable: folder.viewable,
			depth: 0,
			parent: null,
			children: [],
			audit,
			own: audit && !audit.results_hidden ? (own.get(folder.id) ?? emptyStats()) : null,
			branch: emptyStats(),
			auditsInBranch: 0,
			descendants: 0
		});
	}
	let root: TreeNode | null = null;
	for (const folder of feed.folders) {
		const n = nodes.get(folder.id)!;
		const p = folder.parent_id ? nodes.get(folder.parent_id) : null;
		if (p) {
			n.parent = p;
			p.children.push(n);
		} else root = n;
	}
	if (!root) return null;

	const rollup = (n: TreeNode, depth: number) => {
		n.depth = depth;
		if (n.own) {
			merge(n.branch, n.own);
			n.auditsInBranch++;
		}
		for (const c of n.children) {
			rollup(c, depth + 1);
			merge(n.branch, c.branch);
			n.auditsInBranch += c.auditsInBranch;
			n.descendants += 1 + c.descendants;
		}
	};
	rollup(root, 0);
	return root;
}

/** Branch value of `n`, where `ownOf` gives the stats a domain's own audit contributes. */
export function aggregate(
	n: TreeNode,
	ownOf: (n: TreeNode) => Stats | null,
	value: (s: Stats | null) => number | null,
	agg: Aggregation
): number | null {
	const mean = (xs: (number | null)[]) => {
		const v = xs.filter((x): x is number => x !== null);
		return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
	};
	if (agg === 'pooled') {
		const s = emptyStats();
		const walk = (m: TreeNode) => {
			const o = ownOf(m);
			if (o) merge(s, o);
			m.children.forEach(walk);
		};
		walk(n);
		return value(s);
	}
	if (agg === 'audits') {
		const vals: (number | null)[] = [];
		const walk = (m: TreeNode) => {
			vals.push(value(ownOf(m)));
			m.children.forEach(walk);
		};
		walk(n);
		return mean(vals);
	}
	return mean([value(ownOf(n)), ...n.children.map((c) => aggregate(c, ownOf, value, agg))]);
}

/** Pre-order list of every node. */
export function allNodes(root: TreeNode): TreeNode[] {
	const out: TreeNode[] = [];
	const walk = (n: TreeNode) => {
		out.push(n);
		n.children.forEach(walk);
	};
	walk(root);
	return out;
}

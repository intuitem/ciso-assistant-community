import type { Audit, Dataset, Row } from './data';

export type Metric = 'compliance' | 'score';

export interface Stats {
	rows: number;
	compliant: number;
	partial: number;
	nonCompliant: number;
	notApplicable: number;
	notAssessed: number;
	scoreSum: number;
	scored: number;
}

export interface TreeNode {
	id: string;
	name: string;
	depth: number;
	parent: TreeNode | null;
	children: TreeNode[];
	audit: Audit | null;
	own: Stats | null;
	branch: Stats;
	auditsInBranch: number;
	x: number;
	y: number;
}

export interface Filters {
	ig: string | null;
	section: string | null;
}

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

export function addRow(s: Stats, r: Row) {
	s.rows++;
	if (r.result === 'compliant') s.compliant++;
	else if (r.result === 'partially_compliant') s.partial++;
	else if (r.result === 'non_compliant') s.nonCompliant++;
	else if (r.result === 'not_applicable') s.notApplicable++;
	else s.notAssessed++;
	if (r.score !== null && r.result !== 'not_applicable') {
		s.scoreSum += r.score;
		s.scored++;
	}
}

function merge(into: Stats, from: Stats) {
	for (const k of Object.keys(into) as (keyof Stats)[]) into[k] += from[k];
}

export function assessed(s: Stats) {
	return s.compliant + s.partial + s.nonCompliant;
}

/** 0..100, or null when nothing measurable. */
export function metricValue(s: Stats | null, metric: Metric, maxScore: number): number | null {
	if (!s) return null;
	if (metric === 'compliance') {
		const d = assessed(s);
		return d ? (s.compliant / d) * 100 : null;
	}
	return s.scored ? (s.scoreSum / s.scored / maxScore) * 100 : null;
}

export function progressValue(s: Stats | null): number | null {
	if (!s) return null;
	const d = s.rows - s.notApplicable;
	return d ? (assessed(s) / d) * 100 : null;
}

export type Aggregation = 'audits' | 'pooled' | 'children';

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

export function rowMatches(r: Row, f: Filters) {
	if (f.ig && !r.implementation_groups.includes(f.ig)) return false;
	if (f.section && r.section !== f.section) return false;
	return true;
}

export function buildTree(ds: Dataset, filters: Filters): TreeNode | null {
	const auditByFolder = new Map(ds.audits.map((a) => [a.folder_id, a]));
	const ownByFolder = new Map<string, Stats>();
	for (const r of ds.rows) {
		if (!rowMatches(r, filters)) continue;
		let s = ownByFolder.get(r.folder_id);
		if (!s) ownByFolder.set(r.folder_id, (s = emptyStats()));
		addRow(s, r);
	}

	const nodes = new Map<string, TreeNode>();
	for (const f of ds.folders) {
		const audit = auditByFolder.get(f.id) ?? null;
		nodes.set(f.id, {
			id: f.id,
			name: f.name,
			depth: 0,
			parent: null,
			children: [],
			audit,
			own: audit ? (ownByFolder.get(f.id) ?? emptyStats()) : null,
			branch: emptyStats(),
			auditsInBranch: 0,
			x: 0,
			y: 0
		});
	}
	let root: TreeNode | null = null;
	for (const f of ds.folders) {
		const n = nodes.get(f.id)!;
		const p = f.parent_id ? nodes.get(f.parent_id) : null;
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
		}
	};
	rollup(root, 0);
	return root;
}

/** Left-to-right tidy layout: leaves evenly spaced, parents centred on their children. */
export function layout(
	root: TreeNode,
	collapsed: Set<string>,
	colW: number,
	rowH: number
): { nodes: TreeNode[]; edges: [TreeNode, TreeNode][]; width: number; height: number } {
	const nodes: TreeNode[] = [];
	const edges: [TreeNode, TreeNode][] = [];
	let leaf = 0;
	let maxDepth = 0;
	const visit = (n: TreeNode) => {
		nodes.push(n);
		maxDepth = Math.max(maxDepth, n.depth);
		n.x = n.depth * colW;
		const kids = collapsed.has(n.id) ? [] : n.children;
		if (!kids.length) {
			n.y = leaf++ * rowH;
			return;
		}
		for (const c of kids) {
			edges.push([n, c]);
			visit(c);
		}
		n.y = (kids[0].y + kids[kids.length - 1].y) / 2;
	};
	visit(root);
	return { nodes, edges, width: maxDepth * colW, height: Math.max(0, leaf - 1) * rowH };
}

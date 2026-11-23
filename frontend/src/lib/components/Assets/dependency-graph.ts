export type Status = 'cause' | 'impacted' | 'ok' | 'none';

export type Gap = { objective: string; expected: number; actual: number };

export type DependencyNode = {
	id: string;
	label: string;
	type: 'PR' | 'SP';
	domain: string;
	domain_name: string;
	depth: number;
	status: Status;
	gaps: Gap[];
	causes: string[];
};

export type DependencyData = {
	roots: string[];
	nodes: DependencyNode[];
	links: { source: string; target: string; extra: boolean }[];
};

export type DependencyGraph = DependencyData & {
	byId: Record<string, DependencyNode>;
	parents: Record<string, string[]>;
	children: Record<string, string[]>;
	domainColor: Record<string, string>;
	domainName: Record<string, string>;
	impacts: Record<string, string[]>;
};

const DOMAIN_COLORS = [
	'#7b61c9',
	'#2a8fb8',
	'#d0742c',
	'#4c9a4a',
	'#b8508f',
	'#8a7a3a',
	'#3d6fd1',
	'#a3483c'
];

const RECOVERY = ['rto', 'rpo', 'mtd'];

export const STATUS_ORDER: Status[] = ['cause', 'impacted', 'ok', 'none'];

export const STATUS_CLASS: Record<
	Status,
	{ fill: string; stroke: string; bar: string; bg: string }
> = {
	cause: {
		fill: 'fill-error-500/15',
		stroke: 'stroke-error-500',
		bar: 'fill-error-500',
		bg: 'bg-error-500'
	},
	impacted: {
		fill: 'fill-warning-500/15',
		stroke: 'stroke-warning-500',
		bar: 'fill-warning-500',
		bg: 'bg-warning-500'
	},
	ok: {
		fill: 'fill-success-500/15',
		stroke: 'stroke-success-500',
		bar: 'fill-success-500',
		bg: 'bg-success-500'
	},
	none: {
		fill: 'fill-surface-500/10',
		stroke: 'stroke-surface-400',
		bar: 'fill-surface-400',
		bg: 'bg-surface-400'
	}
};

export function buildGraph(data: DependencyData): DependencyGraph {
	const byId = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
	const parents: Record<string, string[]> = {};
	const children: Record<string, string[]> = {};
	const impacts: Record<string, string[]> = {};
	for (const n of data.nodes) {
		parents[n.id] = [];
		children[n.id] = [];
	}
	for (const l of data.links) {
		parents[l.source].push(l.target);
		children[l.target].push(l.source);
	}
	for (const n of data.nodes) for (const c of n.causes) (impacts[c] ??= []).push(n.id);
	const domainName = Object.fromEntries(data.nodes.map((n) => [n.domain, n.domain_name]));
	const domains = Object.keys(domainName).sort((a, b) =>
		domainName[a].localeCompare(domainName[b])
	);
	const domainColor = Object.fromEntries(
		domains.map((d, i) => [d, DOMAIN_COLORS[i % DOMAIN_COLORS.length]])
	);
	return { ...data, byId, parents, children, domainColor, domainName, impacts };
}

export function closure(edges: Record<string, string[]>, id: string): Set<string> {
	const seen = new Set([id]);
	const queue = [id];
	while (queue.length) {
		for (const next of edges[queue.pop()!]) {
			if (!seen.has(next)) {
				seen.add(next);
				queue.push(next);
			}
		}
	}
	return seen;
}

export function formatValue(objective: string, value: number): string {
	if (!RECOVERY.includes(objective)) return String(value);
	if (value < 60) return `${value} s`;
	return value >= 3600 ? `${+(value / 3600).toFixed(1)} h` : `${Math.round(value / 60)} min`;
}

export function formatGap(gap: Gap): string {
	const sign = RECOVERY.includes(gap.objective) ? '>' : '<';
	return `${gap.objective} ${formatValue(gap.objective, gap.actual)} ${sign} ${formatValue(gap.objective, gap.expected)}`;
}

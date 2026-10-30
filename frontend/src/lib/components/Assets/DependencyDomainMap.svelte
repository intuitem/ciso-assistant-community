<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import {
		STATUS_CLASS,
		STATUS_ORDER,
		type DependencyGraph,
		type DependencyNode
	} from './dependency-graph';

	interface Props {
		graph: DependencyGraph;
		onselectcell: (nodes: DependencyNode[]) => void;
	}

	let { graph, onselectcell }: Props = $props();

	const CW = 150;
	const CH = 64;
	const GX = 110;
	const GY = 22;
	const LX = 140;
	const TY = 34;

	const depths = $derived([...new Set(graph.nodes.map((n) => n.depth))].sort((a, b) => a - b));
	const domains = $derived(Object.keys(graph.domainColor));
	const x = (depth: number) => LX + depths.indexOf(depth) * (CW + GX);
	const y = (domain: string) => TY + domains.indexOf(domain) * (CH + GY);

	const cells = $derived.by(() => {
		const out: Record<string, DependencyNode[]> = {};
		for (const n of graph.nodes) (out[`${n.domain}|${n.depth}`] ??= []).push(n);
		return Object.values(out);
	});

	const ribbons = $derived.by(() => {
		const out: Record<
			string,
			{ from: DependencyNode; to: DependencyNode; count: number; gaps: number }
		> = {};
		for (const l of graph.links) {
			const from = graph.byId[l.target];
			const to = graph.byId[l.source];
			if (from.depth >= to.depth) continue;
			const r = (out[`${from.domain}|${from.depth}>${to.domain}|${to.depth}`] ??= {
				from,
				to,
				count: 0,
				gaps: 0
			});
			r.count++;
			if (to.status === 'cause' || to.status === 'impacted') r.gaps++;
		}
		return Object.values(out);
	});
	const maxCount = $derived(Math.max(1, ...ribbons.map((r) => r.count)));

	const width = $derived(LX + depths.length * (CW + GX));
	const height = $derived(TY + domains.length * (CH + GY));

	const count = (nodes: DependencyNode[], status: string) =>
		nodes.filter((n) => n.status === status).length;
</script>

<div class="h-full overflow-auto">
	<svg {width} {height} role="img" aria-label={m.domainMap()}>
		{#each depths as d (d)}
			<text
				x={x(d) + CW / 2}
				y="16"
				font-size="11"
				text-anchor="middle"
				class="fill-surface-600-400 uppercase"
				>{d === 0 ? m.assessedAssets() : m.depthLevel({ depth: d })}</text
			>
		{/each}
		{#each domains as domain (domain)}
			<text
				x="0"
				y={y(domain) + CH / 2 + 4}
				font-size="12"
				font-weight="500"
				fill={graph.domainColor[domain]}
				>{graph.domainName[domain].length > 20
					? `${graph.domainName[domain].slice(0, 19)}…`
					: graph.domainName[domain]}</text
			>
		{/each}
		{#each ribbons as r (`${r.from.domain}|${r.from.depth}>${r.to.domain}|${r.to.depth}`)}
			{@const x1 = x(r.from.depth) + CW}
			{@const y1 = y(r.from.domain) + CH / 2}
			{@const x2 = x(r.to.depth)}
			{@const y2 = y(r.to.domain) + CH / 2}
			{@const mx = (x1 + x2) / 2}
			<path
				d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"
				fill="none"
				stroke-linecap="round"
				class={r.gaps
					? 'stroke-error-500'
					: r.from.domain !== r.to.domain
						? 'stroke-primary-500'
						: 'stroke-surface-400'}
				stroke-width={1 + 9 * Math.sqrt(r.count / maxCount)}
				opacity={r.gaps ? 0.35 + (0.4 * r.gaps) / r.count : 0.35}
			>
				<title>{r.count} · {r.from.domain_name} → {r.to.domain_name}</title>
			</path>
		{/each}
		{#each cells as nodes (`${nodes[0].domain}|${nodes[0].depth}`)}
			{@const n = nodes[0]}
			{@const causes = count(nodes, 'cause')}
			{@const impacted = count(nodes, 'impacted')}
			<g
				transform="translate({x(n.depth)},{y(n.domain)})"
				class="cursor-pointer"
				role="button"
				tabindex="0"
				onclick={() => onselectcell(nodes)}
				onkeydown={(e) => e.key === 'Enter' && onselectcell(nodes)}
			>
				<title>{n.domain_name} · {nodes.length}</title>
				<rect
					width={CW}
					height={CH}
					rx="7"
					class="fill-surface-50-950 {causes ? 'stroke-error-500' : 'stroke-surface-300-700'}"
					stroke-width={causes ? 1.6 : 1}
				/>
				<rect width="5" height={CH} rx="2" fill={graph.domainColor[n.domain]} />
				<text x="12" y="22" font-size="18" font-weight="600" class="fill-surface-950-50"
					>{nodes.length}</text
				>
				<text
					x={CW - 10}
					y="20"
					font-size="11.5"
					text-anchor="end"
					class={causes ? 'fill-error-500' : 'fill-surface-600-400'}
				>
					{causes
						? m.causesCount({ count: causes })
						: impacted
							? m.impactedCount({ count: impacted })
							: count(nodes, 'ok')
								? m.objectivesMet()
								: m.noData()}
				</text>
				{#each STATUS_ORDER as status (status)}
					{@const before = STATUS_ORDER.slice(0, STATUS_ORDER.indexOf(status)).reduce(
						(sum, s) => sum + count(nodes, s),
						0
					)}
					<rect
						x={10 + ((CW - 20) * before) / nodes.length}
						y={CH - 16}
						width={((CW - 20) * count(nodes, status)) / nodes.length}
						height="7"
						class={STATUS_CLASS[status].bar}
					/>
				{/each}
			</g>
		{/each}
	</svg>
</div>

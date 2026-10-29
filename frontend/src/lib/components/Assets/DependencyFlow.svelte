<script lang="ts">
	import dagre from '@dagrejs/dagre';
	import { m } from '#paraglide/messages.js';
	import { STATUS_CLASS, closure, type DependencyGraph } from './dependency-graph';

	interface Props {
		graph: DependencyGraph;
		prune: boolean;
		selected: string | null;
		onselect: (id: string | null) => void;
	}

	let { graph, prune, selected, onselect }: Props = $props();

	const W = 180;
	const H = 28;
	const PAD = 20;

	const visible = $derived(
		new Set(
			graph.nodes
				.filter(
					(n) =>
						!prune || n.status === 'cause' || n.status === 'impacted' || graph.roots.includes(n.id)
				)
				.map((n) => n.id)
		)
	);
	const links = $derived(graph.links.filter((l) => visible.has(l.source) && visible.has(l.target)));

	const layout = $derived.by(() => {
		const g = new dagre.graphlib.Graph();
		g.setGraph({ rankdir: 'LR', ranksep: 90, nodesep: 8, ranker: 'tight-tree' });
		g.setDefaultEdgeLabel(() => ({}));
		for (const id of visible) g.setNode(id, { width: W, height: H });
		for (const l of links) g.setEdge(l.target, l.source);
		dagre.layout(g);
		const pos: Record<string, { x: number; y: number }> = {};
		for (const id of visible) {
			const n = g.node(id);
			pos[id] = { x: n.x - W / 2, y: n.y - H / 2 };
		}
		const { width = 0, height = 0 } = g.graph();
		return { pos, width: width + PAD * 2, height: height + PAD * 2 };
	});

	let view = $state([0, 0, 0, 0]);
	$effect(() => {
		const r = svg.getBoundingClientRect();
		const k = Math.min(1.6, Math.max(layout.width / r.width, layout.height / r.height));
		const ys = graph.roots.filter((id) => layout.pos[id]).map((id) => layout.pos[id].y);
		const rootY = ys.length
			? (Math.min(...ys) + Math.max(...ys)) / 2 + H / 2
			: layout.height / 2 - PAD;
		const h = r.height * k;
		view = [-PAD, Math.max(-PAD, Math.min(rootY - h / 2, layout.height - PAD - h)), r.width * k, h];
	});

	const highlighted = $derived(
		selected && visible.has(selected)
			? new Set([...closure(graph.parents, selected), ...closure(graph.children, selected)])
			: null
	);

	const onGapPath = (source: string) => ['cause', 'impacted'].includes(graph.byId[source].status);

	let svg: SVGSVGElement;
	let drag: [number, number, number, number] | null = null;

	function scale() {
		const r = svg.getBoundingClientRect();
		return Math.max(view[2] / r.width, view[3] / r.height);
	}

	function onwheel(e: WheelEvent) {
		e.preventDefault();
		const r = svg.getBoundingClientRect();
		const s = scale();
		const k = e.deltaY > 0 ? 1.15 : 1 / 1.15;
		const px = view[0] + (e.clientX - r.left - (r.width - view[2] / s) / 2) * s;
		const py = view[1] + (e.clientY - r.top - (r.height - view[3] / s) / 2) * s;
		view = [px - (px - view[0]) * k, py - (py - view[1]) * k, view[2] * k, view[3] * k];
	}

	$effect(() => {
		svg.addEventListener('wheel', onwheel, { passive: false });
		return () => svg.removeEventListener('wheel', onwheel);
	});

	function onpointerdown(e: PointerEvent) {
		if ((e.target as Element).closest('[data-node]')) return;
		drag = [e.clientX, e.clientY, view[0], view[1]];
		svg.setPointerCapture(e.pointerId);
	}

	function onpointermove(e: PointerEvent) {
		if (!drag) return;
		const s = scale();
		view = [
			drag[2] - (e.clientX - drag[0]) * s,
			drag[3] - (e.clientY - drag[1]) * s,
			view[2],
			view[3]
		];
	}

	function truncate(label: string) {
		return label.length > 25 ? `${label.slice(0, 24)}…` : label;
	}
</script>

<div class="relative h-full">
	<svg
		bind:this={svg}
		class="w-full h-full cursor-grab select-none"
		viewBox={view.join(' ')}
		role="img"
		aria-label={m.dependencyFlow()}
		{onpointerdown}
		{onpointermove}
		onpointerup={() => (drag = null)}
	>
		{#each links as l (l.source + l.target)}
			{@const a = layout.pos[l.target]}
			{@const b = layout.pos[l.source]}
			{@const mx = (a.x + W + b.x) / 2}
			{@const crossDomain = graph.byId[l.source].domain !== graph.byId[l.target].domain}
			{@const gap = onGapPath(l.source)}
			<path
				d="M{a.x + W},{a.y + H / 2} C{mx},{a.y + H / 2} {mx},{b.y + H / 2} {b.x},{b.y + H / 2}"
				fill="none"
				class={gap
					? 'stroke-error-500'
					: l.extra
						? 'stroke-tertiary-500'
						: crossDomain
							? 'stroke-primary-500'
							: 'stroke-surface-400'}
				stroke-width={l.extra ? 2 : gap ? 1.4 : 1}
				stroke-dasharray={l.extra ? '1 4' : crossDomain ? '4 3' : undefined}
				stroke-linecap={l.extra ? 'round' : undefined}
				opacity={!highlighted || (highlighted.has(l.source) && highlighted.has(l.target))
					? 0.6
					: 0.06}
			/>
		{/each}
		{#each [...visible] as id (id)}
			{@const n = graph.byId[id]}
			{@const p = layout.pos[id]}
			<g
				data-node
				transform="translate({p.x},{p.y})"
				opacity={!highlighted || highlighted.has(id) ? 1 : 0.15}
				class="cursor-pointer"
				role="button"
				tabindex="0"
				onclick={() => onselect(selected === id ? null : id)}
				onkeydown={(e) => e.key === 'Enter' && onselect(selected === id ? null : id)}
			>
				<title>{n.label} · {n.domain_name}</title>
				{#if graph.roots.includes(id)}
					<circle cx="-8" cy={H / 2} r="4" class="fill-primary-500" />
				{/if}
				<rect width={W} height={H} rx="5" class="fill-surface-50-950" />
				<rect
					width={W}
					height={H}
					rx="5"
					class="{STATUS_CLASS[n.status].fill} {selected === id
						? 'stroke-surface-950-50'
						: STATUS_CLASS[n.status].stroke}"
					stroke-width={selected === id ? 2 : n.status === 'cause' ? 1.6 : 0.8}
				/>
				<rect width="5" height={H} rx="2" fill={graph.domainColor[n.domain]} />
				<text
					x="12"
					y="18"
					font-size="11.5"
					font-weight={n.type === 'PR' ? 600 : 400}
					class="fill-surface-950-50">{truncate(n.label)}</text
				>
				{#if n.status === 'cause'}
					<text
						x={W - 8}
						y="18"
						font-size="11"
						font-weight="600"
						text-anchor="end"
						class="fill-error-500">{n.gaps.length}✕</text
					>
				{/if}
			</g>
		{/each}
	</svg>
	<div class="absolute left-3 bottom-2 text-xs text-surface-600-400 bg-surface-50-950 px-2 rounded">
		{m.assetsShown({ shown: visible.size, total: graph.nodes.length })} · {m.dependencyGraphHint()}
	</div>
</div>

<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { select } from 'd3-selection';
	import { zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom';
	import RingGlyph from './RingGlyph.svelte';
	import { formatPercent } from './format';
	import { tidyLayout, type Placed } from './layout';
	import type { RingColor, RingNode } from './types';

	interface Props {
		root: RingNode;
		collapsed: Set<string>;
		only?: Set<string>;
		/** No collapse toggles (e.g. while a focus filter is on). */
		locked?: boolean;
		selectedId?: string | null;
		color: RingColor;
		/** Refit the view whenever this changes. */
		fitKey?: unknown;
		height?: string;
		onselect?: (id: string) => void;
		ontoggle?: (id: string) => void;
	}

	let {
		root,
		collapsed,
		only,
		locked = false,
		selectedId = null,
		color,
		fitKey,
		height = '70vh',
		onselect,
		ontoggle
	}: Props = $props();

	const COL_W = 230;
	const ROW_H = 135;
	const R_OUT = 34;
	const R_IN = 23;
	const PAD = { x: 110, top: 75, bottom: 70 };
	const uid = $props.id();
	const markerId = `ring-tree-arrow-${uid}`;

	const view = $derived(tidyLayout(root, collapsed, only, COL_W, ROW_H));
	const expandable = (n: RingNode) =>
		!locked && (only ? n.children.some((c) => only.has(c.id)) : n.children.length > 0);

	let svgEl: SVGSVGElement | undefined = $state();
	let behavior: ZoomBehavior<SVGSVGElement, unknown> | undefined;
	let t = $state({ x: 0, y: 0, k: 1 });
	// Keep refitting on resize until the user moves the view themselves.
	let autoFit = true;

	function apply(x: number, y: number, k: number) {
		if (!svgEl || !behavior) return;
		select(svgEl).call(behavior.transform, zoomIdentity.translate(x, y).scale(k));
	}

	export function fit() {
		if (!svgEl) return;
		const { x0, y0, x1, y1 } = view.bounds;
		const w = x1 - x0 + 2 * PAD.x;
		const h = y1 - y0 + PAD.top + PAD.bottom;
		const W = svgEl.clientWidth;
		const H = svgEl.clientHeight;
		const k = Math.max(0.15, Math.min(1, W / w, H / h));
		apply(
			W / 2 - (k * (x0 + x1)) / 2,
			H / 2 - k * (y0 + (y1 - y0) / 2 + (PAD.bottom - PAD.top) / 2),
			k
		);
		autoFit = true;
	}

	export function centerOn(id: string) {
		const p = view.byId.get(id);
		if (!p || !svgEl) return;
		const k = Math.max(t.k, 0.8);
		apply(svgEl.clientWidth / 2 - k * p.x, svgEl.clientHeight / 2 - k * p.y, k);
		autoFit = false;
	}

	function zoomBy(factor: number) {
		if (svgEl && behavior) select(svgEl).call(behavior.scaleBy, factor);
		autoFit = false;
	}

	onMount(() => {
		if (!svgEl) return;
		const el = svgEl;
		behavior = zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.15, 2.5])
			.on('zoom', (e) => {
				if (e.sourceEvent) autoFit = false;
				t = { x: e.transform.x, y: e.transform.y, k: e.transform.k };
			});
		const sel = select(el).call(behavior).on('dblclick.zoom', null);
		const resize = new ResizeObserver(() => autoFit && fit());
		resize.observe(el);
		fit();
		return () => {
			resize.disconnect();
			sel.on('.zoom', null);
		};
	});

	$effect(() => {
		void fitKey;
		untrack(() => fit());
	});

	function edgePath(a: Placed, b: Placed) {
		const x1 = a.x + R_OUT + 20;
		const x2 = b.x - R_OUT - 8;
		const mx = (x1 + x2) / 2;
		return `M${x1},${a.y} C${mx},${a.y} ${mx},${b.y} ${x2},${b.y}`;
	}

	const fmt = formatPercent;

	function activate(e: KeyboardEvent, run: () => void) {
		if (e.key !== 'Enter' && e.key !== ' ') return;
		e.preventDefault();
		e.stopPropagation();
		run();
	}
</script>

<div class="relative">
	<svg
		bind:this={svgEl}
		class="block w-full cursor-grab touch-none text-surface-800-200 active:cursor-grabbing"
		style="height: {height}"
		role="tree"
	>
		<defs>
			<marker
				id={markerId}
				viewBox="0 0 10 10"
				refX="9"
				refY="5"
				markerWidth="7"
				markerHeight="7"
				orient="auto-start-reverse"
			>
				<path d="M0,0 L10,5 L0,10" fill="none" stroke="currentColor" stroke-width="1.5" />
			</marker>
		</defs>
		<g transform="translate({t.x},{t.y}) scale({t.k})">
			{#each view.edges as [a, b] (b.node.id)}
				<path
					d={edgePath(a, b)}
					fill="none"
					stroke="currentColor"
					stroke-opacity="0.35"
					stroke-width="1.5"
					marker-end="url(#{markerId})"
				/>
			{/each}

			{#each view.nodes as p (p.node.id)}
				{@const n = p.node}
				<g
					transform="translate({p.x},{p.y})"
					data-node-id={n.id}
					class="group cursor-pointer outline-hidden"
					role="treeitem"
					aria-selected={selectedId === n.id}
					tabindex="0"
					onclick={() => onselect?.(n.id)}
					onkeydown={(e) => activate(e, () => onselect?.(n.id))}
				>
					<circle
						r={R_OUT + 13}
						fill="none"
						stroke="var(--color-primary-500)"
						stroke-width="2"
						stroke-dasharray="4 3"
						class="hidden group-focus-visible:inline"
					/>
					<title
						>{n.label}: {n.own !== undefined ? `own ${fmt(n.own)}` : ''}{n.showBranch !== false
							? `${n.own !== undefined ? ' · ' : ''}branch ${fmt(n.branch)}`
							: ''}{n.warningDetail ? `\n${n.warningDetail}` : ''}</title
					>
					{#if selectedId === n.id}
						<circle
							r={R_OUT + 8}
							fill="none"
							stroke="var(--color-primary-500)"
							stroke-width="2.5"
						/>
					{/if}
					<circle r={R_OUT + 4} class="fill-surface-50-950" />
					{#if n.badge}
						<text
							x={-R_OUT - 4}
							y={-R_OUT + 4}
							text-anchor="end"
							font-size="12"
							font-weight="700"
							fill="var(--color-primary-500)">{n.badge}</text
						>
					{/if}
					<RingGlyph
						own={n.own}
						faint={n.faint}
						ownSegments={n.ownSegments}
						branch={n.branch}
						showBranch={n.showBranch}
						empty={n.empty}
						{color}
						rOut={R_OUT}
						rIn={R_IN}
						wOut={4}
						wIn={9}
					/>
					{#if n.own !== undefined}
						<text
							text-anchor="middle"
							dy="0.35em"
							font-size="13"
							font-weight="700"
							fill="currentColor"
							fill-opacity={n.faint ? 0.5 : 1}
							>{n.ownLabel ?? fmt(n.own)}{#if n.warning}<tspan
									font-size="10"
									dy="-5"
									fill="var(--color-warning-500)"
									fill-opacity="1">◔</tspan
								>{/if}</text
						>
						{#if n.showBranch !== false}
							<text
								text-anchor="middle"
								y={-R_OUT - 10}
								font-size="11"
								fill="currentColor"
								fill-opacity="0.65">branch {fmt(n.branch)}</text
							>
						{/if}
					{:else}
						<text
							text-anchor="middle"
							dy="0.35em"
							font-size="13"
							font-weight="600"
							fill="currentColor"
							fill-opacity="0.65">{fmt(n.branch)}</text
						>
					{/if}
					<text
						text-anchor="middle"
						y={R_OUT + 20}
						font-size="13"
						font-weight="600"
						font-style={n.muted ? 'italic' : 'normal'}
						fill="currentColor"
						fill-opacity={n.muted ? 0.6 : 1}
						>{n.label}{collapsed.has(n.id) && n.hiddenCount ? ` +${n.hiddenCount}` : ''}</text
					>
					{#if n.sublabel}
						<text text-anchor="middle" y={R_OUT + 35} font-size="10.5" fill="currentColor"
							><tspan fill-opacity="0.55">{n.sublabel}</tspan>{#if n.warning}<tspan
									fill="var(--color-warning-600)">{` · ${n.warning}`}</tspan
								>{/if}</text
						>
					{/if}
					{#if expandable(n)}
						<g
							transform="translate({R_OUT + 12},0)"
							role="button"
							tabindex="0"
							aria-label={collapsed.has(n.id) ? 'Expand' : 'Collapse'}
							onclick={(e) => {
								e.stopPropagation();
								ontoggle?.(n.id);
							}}
							onkeydown={(e) => activate(e, () => ontoggle?.(n.id))}
						>
							<circle
								r="8"
								class="fill-surface-50-950"
								stroke="currentColor"
								stroke-opacity="0.4"
							/>
							<text text-anchor="middle" dy="0.35em" font-size="12" fill="currentColor"
								>{collapsed.has(n.id) ? '+' : '−'}</text
							>
						</g>
					{/if}
				</g>
			{/each}
		</g>
	</svg>

	<div class="absolute right-2 bottom-2 flex flex-col gap-1">
		<button
			class="btn-icon btn-icon-sm preset-tonal"
			aria-label="Zoom in"
			onclick={() => zoomBy(1.25)}><i class="fa-solid fa-plus"></i></button
		>
		<button
			class="btn-icon btn-icon-sm preset-tonal"
			aria-label="Zoom out"
			onclick={() => zoomBy(0.8)}><i class="fa-solid fa-minus"></i></button
		>
		<button class="btn-icon btn-icon-sm preset-tonal" aria-label="Fit to view" onclick={fit}
			><i class="fa-solid fa-expand"></i></button
		>
		{#if selectedId}
			<button
				class="btn-icon btn-icon-sm preset-tonal"
				aria-label="Center on selection"
				onclick={() => selectedId && centerOn(selectedId)}
				><i class="fa-solid fa-crosshairs"></i></button
			>
		{/if}
	</div>
</div>

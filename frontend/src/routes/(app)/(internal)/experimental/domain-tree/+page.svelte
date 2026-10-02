<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { generateDataset } from './data';
	import {
		addRow,
		aggregate,
		AGGREGATIONS,
		assessed,
		buildTree,
		emptyStats,
		layout,
		metricValue,
		progressValue,
		rowMatches,
		type Aggregation,
		type Metric,
		type Stats,
		type TreeNode
	} from './tree';

	$pageTitle = 'Domain compliance tree';

	const COL_W = 230;
	const ROW_H = 135;
	const PAD = { left: 60, top: 70, right: 170, bottom: 90 };
	const R_OUT = 34;
	const R_IN = 23;
	const C_OUT = 2 * Math.PI * R_OUT;
	const C_IN = 2 * Math.PI * R_IN;

	let seed = $state(42);
	let ig = $state<string>('');
	let section = $state<string>('');
	let metric = $state<Metric>('compliance');
	let agg = $state<Aggregation>('audits');
	let collapsed = $state<Set<string>>(new Set());
	let selectedId = $state<string | null>(null);

	const ds = $derived(generateDataset(seed));
	const maxScore = $derived(ds.framework.max_score);
	const filters = $derived({ ig: ig || null, section: section || null });
	const root = $derived(buildTree(ds, filters));
	const view = $derived(root ? layout(root, collapsed, COL_W, ROW_H) : null);
	const byId = $derived(new Map((view?.nodes ?? []).map((n) => [n.id, n])));
	const selected = $derived(selectedId ? (byId.get(selectedId) ?? null) : null);

	const scopeSize = $derived(
		ds.requirements.filter(
			(r) =>
				(!filters.ig || r.implementation_groups.includes(filters.ig)) &&
				(!filters.section || r.section === filters.section)
		).length
	);

	function val(s: Stats | null) {
		return metricValue(s, metric, maxScore);
	}

	function branchVal(n: TreeNode) {
		return aggregate(n, (m) => m.own, val, agg);
	}

	const caption = $derived(
		[
			ds.framework.name,
			metric === 'compliance' ? 'Compliance' : 'Score',
			filters.ig ?? "each audit's own IGs",
			filters.section
				? `section ${filters.section}. ${ds.sections.find((s) => s.ref_id === filters.section)?.name}`
				: 'all sections'
		].join(' · ')
	);
	const aggCaption = $derived(AGGREGATIONS.find((a) => a.key === agg)?.caption);

	function fmt(v: number | null) {
		return v === null ? '—' : `${Math.round(v)}%`;
	}

	function color(v: number | null) {
		if (v === null) return 'var(--color-surface-400)';
		if (v < 40) return 'var(--color-error-500)';
		if (v < 70) return 'var(--color-warning-500)';
		return 'var(--color-success-500)';
	}

	function toggle(id: string, e: Event) {
		e.stopPropagation();
		const next = new Set(collapsed);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		collapsed = next;
	}

	function edgePath(a: TreeNode, b: TreeNode) {
		const x1 = a.x + R_OUT + 20;
		const x2 = b.x - R_OUT - 8;
		const mx = (x1 + x2) / 2;
		return `M${x1},${a.y} C${mx},${a.y} ${mx},${b.y} ${x2},${b.y}`;
	}

	function subtitle(n: TreeNode) {
		if (n.audit) {
			const igs = n.audit.selected_implementation_groups;
			const scope = igs.length ? ` · ${igs.join('+')} only` : '';
			return `${n.audit.status.replace('_', ' ')}${scope}`;
		}
		if (n.auditsInBranch) return `no audit · ${n.auditsInBranch} below`;
		return 'no audit data';
	}

	const branchFolders = $derived.by(() => {
		const ids = new Set<string>();
		const walk = (n: TreeNode) => {
			ids.add(n.id);
			n.children.forEach(walk);
		};
		if (selected) walk(selected);
		return ids;
	});

	const sectionBreakdown = $derived.by(() => {
		if (!selected) return [];
		const per = new Map<string, Stats>();
		for (const r of ds.rows) {
			if (!branchFolders.has(r.folder_id)) continue;
			if (!rowMatches(r, { ig: filters.ig, section: null })) continue;
			const key = `${r.folder_id}|${r.section}`;
			let s = per.get(key);
			if (!s) per.set(key, (s = emptyStats()));
			addRow(s, r);
		}
		const branchRoot = selected;
		return ds.sections
			.map((sec) => ({
				...sec,
				value: aggregate(
					branchRoot,
					(m) => (m.audit ? (per.get(`${m.id}|${sec.ref_id}`) ?? emptyStats()) : null),
					val,
					agg
				)
			}))
			.filter((s) => s.value !== null)
			.sort((a, b) => (a.value ?? 0) - (b.value ?? 0));
	});

	const sortedChildren = $derived(
		selected
			? [...selected.children].sort((a, b) => (branchVal(a) ?? 101) - (branchVal(b) ?? 101))
			: []
	);

	function segments(s: Stats) {
		return [
			{ label: 'Compliant', n: s.compliant, c: 'var(--color-success-500)' },
			{ label: 'Partially compliant', n: s.partial, c: 'var(--color-warning-500)' },
			{ label: 'Non compliant', n: s.nonCompliant, c: 'var(--color-error-500)' },
			{ label: 'Not assessed', n: s.notAssessed, c: 'var(--color-surface-300)' },
			{ label: 'Not applicable', n: s.notApplicable, c: 'var(--color-surface-500)' }
		].filter((x) => x.n > 0);
	}

	function collapseTo(depth: number | null) {
		if (!view || !root) return;
		const next = new Set<string>();
		if (depth !== null) {
			const walk = (n: TreeNode) => {
				if (n.depth >= depth && n.children.length) next.add(n.id);
				n.children.forEach(walk);
			};
			walk(root);
		}
		collapsed = next;
	}
</script>

{#snippet statBlock(title: string, s: Stats | null, coverage?: number, value?: number | null)}
	{@const v = value === undefined ? val(s) : value}
	<div class="space-y-1">
		<div class="flex items-baseline justify-between">
			<span class="text-xs font-semibold uppercase tracking-wide text-surface-600-400">{title}</span
			>
			<span class="text-lg font-bold" style="color: {color(v)}">{fmt(v)}</span>
		</div>
		{#if s && s.rows}
			<div class="flex h-2 w-full overflow-hidden rounded-full">
				{#each segments(s) as seg (seg.label)}
					<div
						style="width: {(seg.n / s.rows) * 100}%; background: {seg.c}"
						title="{seg.label}: {seg.n}"
					></div>
				{/each}
			</div>
			<div class="flex flex-wrap gap-x-3 text-xs text-surface-600-400">
				<span>{assessed(s)}/{s.rows - s.notApplicable} assessed ({fmt(progressValue(s))})</span>
				{#if metric === 'score'}<span>{s.scored} scored</span>{/if}
				{#if value !== undefined}<span>pooled {fmt(val(s))}</span>{/if}
				{#if coverage !== undefined && coverage < 1}
					<span class="text-warning-700-300">covers {Math.round(coverage * 100)}% of scope</span>
				{/if}
			</div>
		{:else}
			<p class="text-xs text-surface-500">No rows in the current filter.</p>
		{/if}
	</div>
{/snippet}

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-end gap-4">
		<div>
			<div class="text-xs text-surface-600-400">Framework</div>
			<div class="font-semibold">
				{ds.framework.name}
				<span class="ml-1 rounded bg-warning-100-900 px-1.5 py-0.5 text-xs text-warning-800-200"
					>dummy data</span
				>
			</div>
		</div>
		<label class="text-xs text-surface-600-400">
			Implementation group
			<select class="select mt-1 w-36" bind:value={ig}>
				<option value="">Each audit's own</option>
				{#each ds.implementationGroups as g (g)}<option value={g}>{g}</option>{/each}
			</select>
		</label>
		<label class="text-xs text-surface-600-400">
			Section
			<select class="select mt-1 w-64" bind:value={section}>
				<option value="">All sections</option>
				{#each ds.sections as s (s.ref_id)}
					<option value={s.ref_id}>{s.ref_id}. {s.name}</option>
				{/each}
			</select>
		</label>
		<div class="text-xs text-surface-600-400">
			Metric
			<div class="mt-1 flex overflow-hidden rounded-md border border-surface-300-700">
				{#each [['compliance', 'Compliance'], ['score', 'Score']] as [k, label] (k)}
					<button
						class="px-3 py-1.5 text-sm {metric === k
							? 'preset-filled-primary-500'
							: 'hover:bg-surface-100-900'}"
						onclick={() => (metric = k as Metric)}>{label}</button
					>
				{/each}
			</div>
		</div>
		<label class="text-xs text-surface-600-400">
			Branch average
			<select class="select mt-1 w-56" bind:value={agg}>
				{#each AGGREGATIONS as a (a.key)}<option value={a.key}>{a.label}</option>{/each}
			</select>
		</label>
		<div class="ml-auto flex gap-2">
			<button class="btn btn-sm preset-tonal" onclick={() => collapseTo(null)}>Expand all</button>
			<button class="btn btn-sm preset-tonal" onclick={() => collapseTo(1)}>Top level</button>
			<button
				class="btn btn-sm preset-tonal"
				onclick={() => (seed = Math.floor(Math.random() * 1e6))}
				><i class="fa-solid fa-dice mr-1"></i>Regenerate</button
			>
		</div>
	</div>

	<div class="flex flex-wrap items-center gap-5 text-xs text-surface-600-400">
		<span class="flex items-center gap-2">
			<svg width="28" height="28" viewBox="-14 -14 28 28">
				<circle r="12" fill="none" stroke="currentColor" stroke-width="2" opacity="0.5" />
				<circle r="7" fill="none" stroke="currentColor" stroke-width="4" />
			</svg>
			Thick inner ring: the domain's own audit · thin outer ring: whole branch (domain + sub-domains)
		</span>
		<span class="flex items-center gap-2">
			<svg width="28" height="28" viewBox="-14 -14 28 28">
				<circle r="12" fill="none" stroke="currentColor" stroke-width="2" opacity="0.5" />
			</svg>
			Outer ring only: no local audit, branch average
		</span>
		<span class="flex items-center gap-2">
			<span class="h-2.5 w-2.5 rounded-full" style="background: var(--color-error-500)"
			></span>&lt;40%
			<span class="h-2.5 w-2.5 rounded-full" style="background: var(--color-warning-500)"
			></span>&lt;70%
			<span class="h-2.5 w-2.5 rounded-full" style="background: var(--color-success-500)"
			></span>≥70%
		</span>
	</div>

	<div class="flex flex-col gap-4 lg:flex-row">
		<div
			class="min-w-0 flex-1 overflow-x-auto rounded-lg border border-surface-200-800 bg-surface-50-950"
		>
			<div class="border-b border-surface-200-800 px-4 py-2">
				<div class="text-sm font-semibold">{caption}</div>
				<div class="text-xs text-surface-600-400">Branch = {aggCaption}</div>
			</div>
			{#if view}
				<svg
					class="text-surface-800-200"
					width={view.width + PAD.left + PAD.right}
					height={view.height + PAD.top + PAD.bottom}
					role="tree"
				>
					<defs>
						<marker
							id="dt-arrow"
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
					<g transform="translate({PAD.left},{PAD.top})">
						{#each view.edges as [a, b] (b.id)}
							<path
								d={edgePath(a, b)}
								fill="none"
								stroke="currentColor"
								stroke-opacity="0.35"
								stroke-width="1.5"
								marker-end="url(#dt-arrow)"
							/>
						{/each}

						{#each view.nodes as n (n.id)}
							{@const own = n.audit ? val(n.own) : null}
							{@const branch = branchVal(n)}
							{@const empty = !n.auditsInBranch}
							<g
								transform="translate({n.x},{n.y})"
								class="cursor-pointer outline-none"
								role="treeitem"
								aria-selected={selectedId === n.id}
								tabindex="0"
								onclick={() => (selectedId = n.id)}
								onkeydown={(e) => e.key === 'Enter' && (selectedId = n.id)}
							>
								<title>{n.name}: own {fmt(own)} · branch {fmt(branch)}</title>
								{#if selectedId === n.id}
									<circle r={R_OUT + 9} fill="var(--color-primary-500)" fill-opacity="0.12" />
								{/if}
								<circle r={R_OUT + 4} class="fill-surface-50-950" />

								<circle
									r={R_OUT}
									fill="none"
									stroke="currentColor"
									stroke-opacity="0.12"
									stroke-width="4"
									stroke-dasharray={empty ? '4 4' : undefined}
								/>
								{#if branch !== null}
									<circle
										r={R_OUT}
										fill="none"
										stroke={color(branch)}
										stroke-width="4"
										stroke-linecap="round"
										stroke-dasharray="{(branch / 100) * C_OUT} {C_OUT}"
										transform="rotate(-90)"
									/>
								{/if}

								{#if n.audit}
									<circle
										r={R_IN}
										fill="none"
										stroke="currentColor"
										stroke-opacity="0.12"
										stroke-width="9"
									/>
									{#if own !== null}
										<circle
											r={R_IN}
											fill="none"
											stroke={color(own)}
											stroke-width="9"
											stroke-dasharray="{(own / 100) * C_IN} {C_IN}"
											transform="rotate(-90)"
										/>
									{/if}
									<text
										text-anchor="middle"
										dy="0.35em"
										font-size="13"
										font-weight="700"
										fill="currentColor">{fmt(own)}</text
									>
									<text
										text-anchor="middle"
										y={-R_OUT - 10}
										font-size="11"
										fill="currentColor"
										fill-opacity="0.65">branch {fmt(branch)}</text
									>
								{:else}
									<text
										text-anchor="middle"
										dy="0.35em"
										font-size="13"
										font-weight="600"
										fill="currentColor"
										fill-opacity="0.65">{fmt(branch)}</text
									>
								{/if}

								<text
									text-anchor="middle"
									y={R_OUT + 20}
									font-size="13"
									font-weight="600"
									fill="currentColor">{n.name}</text
								>
								<text
									text-anchor="middle"
									y={R_OUT + 35}
									font-size="10.5"
									fill="currentColor"
									fill-opacity="0.55">{subtitle(n)}</text
								>

								{#if n.children.length}
									<g
										transform="translate({R_OUT + 12},0)"
										role="button"
										tabindex="0"
										aria-label={collapsed.has(n.id) ? 'Expand' : 'Collapse'}
										onclick={(e) => toggle(n.id, e)}
										onkeydown={(e) => e.key === 'Enter' && toggle(n.id, e)}
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
			{/if}
		</div>

		<aside class="w-full shrink-0 space-y-4 rounded-lg border border-surface-200-800 p-4 lg:w-96">
			{#if selected}
				<div>
					<h3 class="text-lg font-bold">{selected.name}</h3>
					<p class="text-xs text-surface-600-400">
						{#if selected.audit}
							{selected.audit.name} · {selected.audit.status.replace('_', ' ')}
						{:else}
							No local audit
						{/if}
						· {selected.auditsInBranch} audit{selected.auditsInBranch === 1 ? '' : 's'} in branch
					</p>
				</div>

				{#if selected.audit}
					{@render statBlock(
						'Own audit',
						selected.own,
						selected.own ? selected.own.rows / scopeSize : undefined
					)}
				{/if}
				{@render statBlock(
					'Branch',
					selected.auditsInBranch ? selected.branch : null,
					undefined,
					branchVal(selected)
				)}

				{#if sortedChildren.length}
					<div>
						<div class="mb-1 text-xs font-semibold uppercase tracking-wide text-surface-600-400">
							Sub-domains, weakest first
						</div>
						<ul class="space-y-1">
							{#each sortedChildren as c (c.id)}
								{@const v = branchVal(c)}
								<li>
									<button
										class="flex w-full items-center gap-2 rounded px-1 py-0.5 text-left text-sm hover:bg-surface-100-900"
										onclick={() => (selectedId = c.id)}
									>
										<span class="flex-1 truncate">{c.name}</span>
										<span class="h-1.5 w-20 overflow-hidden rounded-full bg-surface-200-800">
											<span class="block h-full" style="width: {v ?? 0}%; background: {color(v)}"
											></span>
										</span>
										<span class="w-10 text-right font-semibold">{fmt(v)}</span>
									</button>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if sectionBreakdown.length && !filters.section}
					<div>
						<div class="mb-1 text-xs font-semibold uppercase tracking-wide text-surface-600-400">
							Branch by section, weakest first
						</div>
						<ul class="space-y-1">
							{#each sectionBreakdown as s (s.ref_id)}
								<li>
									<button
										class="flex w-full items-center gap-2 rounded px-1 py-0.5 text-left text-xs hover:bg-surface-100-900"
										title="Filter the tree on this section"
										onclick={() => (section = s.ref_id)}
									>
										<span class="w-5 text-right text-surface-500">{s.ref_id}</span>
										<span class="flex-1 truncate">{s.name}</span>
										<span class="h-1.5 w-16 overflow-hidden rounded-full bg-surface-200-800">
											<span
												class="block h-full"
												style="width: {s.value}%; background: {color(s.value)}"
											></span>
										</span>
										<span class="w-9 text-right font-semibold">{fmt(s.value)}</span>
									</button>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			{:else}
				<p class="text-sm text-surface-600-400">
					Click a domain to see its own audit, its branch, its weakest sub-domains and its weakest
					sections.
				</p>
			{/if}
		</aside>
	</div>
</div>

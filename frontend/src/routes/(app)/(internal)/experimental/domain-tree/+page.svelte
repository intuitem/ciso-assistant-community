<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import RingGlyph from '$lib/components/DataViz/RingTree/RingGlyph.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { complianceResultColorMap } from '$lib/utils/constants';
	import { formatPercent } from '$lib/components/DataViz/RingTree/format';
	import RingTree from '$lib/components/DataViz/RingTree/RingTree.svelte';
	import RingOutline from '$lib/components/DataViz/RingTree/RingOutline.svelte';
	import { visibleList } from '$lib/components/DataViz/RingTree/layout';
	import type { RingNode } from '$lib/components/DataViz/RingTree/types';
	import { generateFeed, type FeedSize } from './data';
	import { COUNT } from './feed';
	import {
		aggregate,
		AGGREGATIONS,
		allNodes,
		assessed,
		buildTree,
		emptyStats,
		metricValue,
		ownStats,
		progressValue,
		scopeSize as computeScopeSize,
		type Aggregation,
		type Metric,
		type Stats,
		type TreeNode
	} from './tree';

	$pageTitle = 'Domain compliance tree';

	const OUTLINE_THRESHOLD = 40;
	const MIN_PROGRESS = 50;
	const MIN_ANSWERS = 10;
	// what is left of the window under the toolbars, so the legend stays in view
	const TREE_HEIGHT = 'max(24rem, calc(100vh - 26rem))';

	let seed = $state(42);
	let size = $state<FeedSize>('small');
	let ig = $state<string>('');
	let section = $state<number | null>(null);
	let metric = $state<Metric>('compliance');
	let agg = $state<Aggregation>('audits');
	let collapsed = $state<Set<string>>(new Set());
	let selectedId = $state<string | null>(null);
	let query = $state('');
	let focusN = $state(0);
	let mode = $state<'auto' | 'tree' | 'outline'>('auto');
	let hideEmpty = $state(true);
	let treeRef: RingTree | undefined = $state();
	let outlineRef: RingOutline | undefined = $state();

	let { data } = $props();

	const pickerSchema = z.object({ framework: z.string().nullable().optional() });
	const pickerForm = superForm(
		defaults({ framework: untrack(() => data.frameworkId) ?? null }, zod(pickerSchema)),
		{ dataType: 'json', SPA: true, validators: zod(pickerSchema) }
	);

	function pickFramework(id: string | null | undefined) {
		if (!id || id === data.frameworkId) return;
		openFramework(id);
	}

	function openFramework(id: string | null) {
		const params = new URLSearchParams();
		if (id) params.set('framework', id);
		if (id && data.campaignId) params.set('campaign', data.campaignId);
		goto(`?${params}`, { noScroll: true });
	}

	const isDummy = $derived(!data.frameworkId);

	$effect(() => {
		void data.frameworkId;
		selectedId = null;
		collapsed = new Set();
		focusN = 0;
		ig = '';
		section = null;
	});
	const feed = $derived(data.feed ?? generateFeed(seed, size));
	const hasScores = $derived(
		feed.audits.some((a) => a.score !== null) || feed.counts.some((t) => t[COUNT.scored] > 0)
	);
	const shownMetric = $derived<Metric>(hasScores ? metric : 'compliance');
	const feedKb = $derived(new Blob([JSON.stringify(feed)]).size / 1024);
	const filters = $derived({ ig: ig || null, section });
	const root = $derived(buildTree(feed, filters));
	const nodes = $derived(root ? allNodes(root) : []);
	const nodeById = $derived(new Map(nodes.map((n) => [n.id, n])));
	const selected = $derived(selectedId ? (nodeById.get(selectedId) ?? null) : null);
	const scopeSize = $derived(computeScopeSize(feed, filters));

	function val(s: Stats | null) {
		return metricValue(s, shownMetric);
	}

	const branchById = $derived(
		new Map(nodes.map((n) => [n.id, aggregate(n, (m) => m.own, val, agg)]))
	);

	function branchVal(n: TreeNode) {
		return branchById.get(n.id) ?? null;
	}

	const measured = $derived(nodes.filter((n) => n.audit && val(n.own) !== null));
	const tooEarly = $derived(measured.filter((n) => lowCoverage(n)));
	const weakest = $derived(
		focusN
			? measured
					.filter((n) => !lowCoverage(n))
					.sort((a, b) => val(a.own)! - val(b.own)!)
					.slice(0, focusN)
			: []
	);
	const rank = $derived(new Map(weakest.map((n, i) => [n.id, i + 1])));
	const focusSet = $derived.by(() => {
		if (!focusN) return undefined;
		const ids = new Set<string>();
		for (const n of weakest) for (let a: TreeNode | null = n; a; a = a.parent) ids.add(a.id);
		return ids;
	});
	const withAudits = $derived.by(() => {
		const ids = new Set<string>();
		const mark = (n: TreeNode): boolean => {
			let has = !!n.audit;
			for (const c of n.children) has = mark(c) || has;
			if (has) ids.add(n.id);
			return has;
		};
		if (root) mark(root);
		if (root) ids.add(root.id);
		return ids;
	});
	// audits strictly below each domain, hidden-results ones included
	const auditsBelow = $derived.by(() => {
		const out = new Map<string, number>();
		const count = (n: TreeNode): number => {
			let below = 0;
			for (const c of n.children) below += count(c);
			out.set(n.id, below);
			return below + (n.audit ? 1 : 0);
		};
		if (root) count(root);
		return out;
	});
	const branchAddsInfo = (n: TreeNode) => !n.audit || (auditsBelow.get(n.id) ?? 0) > 0;
	const only = $derived(focusSet ?? (hideEmpty ? withAudits : undefined));
	const shownCollapsed = $derived(focusSet ? new Set<string>() : collapsed);

	function toRing(n: TreeNode): RingNode {
		return {
			id: n.id,
			label: label(n),
			sublabel: subtitle(n),
			muted: !n.viewable,
			own: n.audit ? val(n.own) : undefined,
			ownLabel: allNotApplicable(n.own) ? 'N/A' : undefined,
			faint: lowCoverage(n),
			warning: lowCoverage(n) ? 'low coverage' : undefined,
			warningDetail: coverageNote(n),
			ownSegments: shownMetric === 'compliance' && n.own ? resultSlices(n.own) : undefined,
			branch: branchVal(n),
			showBranch: branchAddsInfo(n),
			empty: !n.auditsInBranch,
			badge: rank.has(n.id) ? `#${rank.get(n.id)}` : undefined,
			hiddenCount: n.descendants,
			children: n.children.map(toRing)
		};
	}
	const ringRoot = $derived(root ? toRing(root) : null);
	const visibleCount = $derived(ringRoot ? visibleList(ringRoot, shownCollapsed, only).length : 0);
	const outline = $derived(
		mode === 'outline' || (mode === 'auto' && visibleCount > OUTLINE_THRESHOLD)
	);
	const fitKey = $derived(`${data.frameworkId}|${seed}|${size}|${focusN}|${outline}`);

	const caption = $derived(
		[
			feed.framework.name,
			shownMetric === 'compliance' ? 'Compliance' : 'Score',
			filters.ig ?? "each audit's own IGs",
			filters.section !== null ? `section ${sectionLabel(filters.section)}` : 'all sections'
		].join(' · ')
	);
	const aggCaption = $derived(AGGREGATIONS.find((a) => a.key === agg)?.caption);
	const captionNotes = $derived(
		[
			`Branch = ${aggCaption}`,
			shownMetric === 'score'
				? filters.ig || filters.section !== null
					? 'score = average of the implementation scores in this filter'
					: "score = each audit's score as on its audit page"
				: '',
			hideEmpty && !focusSet && nodes.length > withAudits.size
				? `${nodes.length - withAudits.size} ${nodes.length - withAudits.size === 1 ? 'domain' : 'domains'} without audits hidden`
				: ''
		]
			.filter(Boolean)
			.join(' · ')
	);

	const matches = $derived.by(() => {
		const q = query.trim().toLowerCase();
		if (q.length < 2) return [];
		return nodes.filter((n) => n.viewable && n.name.toLowerCase().includes(q)).slice(0, 8);
	});

	const fmt = formatPercent;

	function color(v: number | null) {
		if (v === null) return 'var(--color-surface-400)';
		if (v < 40) return 'var(--color-error-500)';
		if (v < 70) return 'var(--color-warning-500)';
		return 'var(--color-success-500)';
	}

	function toggle(id: string) {
		const next = new Set(collapsed);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		collapsed = next;
	}

	function allNotApplicable(s: Stats | null) {
		return !!s && s.rows > 0 && s.rows === s.notApplicable;
	}

	/** Too little behind the figure: the audit page's progress is low, or few answers. */
	function lowCoverage(n: TreeNode) {
		if (!n.audit || !n.own || val(n.own) === null) return false;
		return (n.audit.progress ?? 0) < MIN_PROGRESS || assessed(n.own) < MIN_ANSWERS;
	}

	function coverageNote(n: TreeNode) {
		if (!lowCoverage(n) || !n.own) return undefined;
		const answers = assessed(n.own);
		return answers < MIN_ANSWERS
			? `Based on ${answers} ${answers === 1 ? 'answer' : 'answers'} only (under ${MIN_ANSWERS}): shown faded`
			: `The audit page shows ${n.audit?.progress ?? 0}% progress (under ${MIN_PROGRESS}%): shown faded`;
	}

	function label(n: TreeNode) {
		return n.viewable ? n.name : 'Restricted domain';
	}

	function subtitle(n: TreeNode) {
		if (!n.viewable) return `not viewable · ${n.auditsInBranch} audits below`;
		if (n.audit) {
			const parts = n.audit.results_hidden
				? ['results hidden']
				: [n.audit.progress === null ? '' : `${n.audit.progress}% progress`].filter(Boolean);
			if (n.audit.status) parts.push(n.audit.status.replace('_', ' '));
			const igs = n.audit.selected_implementation_groups;
			if (igs.length) parts.push(`${igs.join('+')} only`);
			return parts.join(' · ');
		}
		if (n.auditsInBranch) return `no audit · ${n.auditsInBranch} below`;
		return 'no audit data';
	}

	function sectionLabel(index: number) {
		const s = feed.sections[index];
		if (!s) return '';
		return s.ref_id ? `${s.ref_id}. ${s.name}` : s.name;
	}

	function statusLabel(status: string | null) {
		return status ? status.replace('_', ' ') : 'no status';
	}

	function path(n: TreeNode) {
		const parts: string[] = [];
		for (let a = n.parent; a; a = a.parent) parts.unshift(label(a));
		return parts.join(' › ');
	}

	async function reveal(n: TreeNode) {
		const next = new Set(collapsed);
		for (let a = n.parent; a; a = a.parent) next.delete(a.id);
		collapsed = next;
		if (focusSet && !focusSet.has(n.id)) focusN = 0;
		if (hideEmpty && !withAudits.has(n.id)) hideEmpty = false;
		selectedId = n.id;
		query = '';
		await tick();
		if (outline) outlineRef?.scrollTo(n.id);
		else treeRef?.centerOn(n.id);
	}

	const sectionBreakdown = $derived.by(() => {
		if (!selected) return [];
		const branchRoot = selected;
		return feed.sections
			.map((sec, index) => {
				const own = ownStats(feed, { ig: filters.ig, section: index });
				return {
					...sec,
					index,
					value: aggregate(
						branchRoot,
						(m) => (m.audit ? (own.get(m.id) ?? emptyStats()) : null),
						val,
						agg
					)
				};
			})
			.filter((s) => s.value !== null)
			.sort((a, b) => (a.value ?? 0) - (b.value ?? 0));
	});

	const sortedChildren = $derived(
		selected
			? [...selected.children].sort((a, b) => (branchVal(a) ?? 101) - (branchVal(b) ?? 101))
			: []
	);

	/** Same slices as the audit page's result donut, over applicable requirements. */
	function resultSlices(s: Stats) {
		const applicable = s.rows - s.notApplicable;
		if (!applicable) return undefined;
		return [
			{ n: s.compliant, color: complianceResultColorMap.compliant },
			{ n: s.partial, color: complianceResultColorMap.partially_compliant },
			{ n: s.nonCompliant, color: complianceResultColorMap.non_compliant }
		]
			.filter((x) => x.n > 0)
			.map((x) => ({ fraction: x.n / applicable, color: x.color }));
	}

	function segments(s: Stats) {
		return [
			{ label: 'Compliant', n: s.compliant, c: complianceResultColorMap.compliant },
			{
				label: 'Partially compliant',
				n: s.partial,
				c: complianceResultColorMap.partially_compliant
			},
			{ label: 'Non compliant', n: s.nonCompliant, c: complianceResultColorMap.non_compliant },
			{
				label: 'Not assessed',
				n: s.notAssessed,
				c: 'color-mix(in srgb, currentColor 15%, transparent)'
			},
			{
				label: 'Not applicable',
				n: s.notApplicable,
				c: 'color-mix(in srgb, currentColor 40%, transparent)'
			}
		].filter((x) => x.n > 0);
	}

	function collapseTo(depth: number | null) {
		if (!root) return;
		focusN = 0;
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
				<span>{assessed(s)}/{s.rows - s.notApplicable} answered ({fmt(progressValue(s))})</span>
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

{#snippet fieldLabel(text: string)}
	<span class="mb-1 block text-xs font-medium text-surface-600-400">{text}</span>
{/snippet}

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-end gap-3">
		<div class="picker min-w-72 flex-1">
			{@render fieldLabel('Framework')}
			<div class="flex gap-1">
				<div class="min-w-0 flex-1">
					<AutocompleteSelect
						form={pickerForm}
						field="framework"
						optionsEndpoint="frameworks"
						optionsDetailedUrlParameters={[['in_domain_tree', 'true']]}
						optionsInfoFields={{ fields: [{ field: 'provider' }], position: 'prefix' }}
						placeholder="Pick a framework"
						onChange={pickFramework}
					/>
				</div>
				{#if !isDummy}
					<button
						type="button"
						class="btn h-9 shrink-0 preset-tonal text-sm"
						onclick={() => {
							pickerForm.form.update((f) => ({ ...f, framework: null }));
							openFramework(null);
						}}>Use dummy data</button
					>
				{/if}
			</div>
		</div>
		<label>
			{@render fieldLabel('Implementation group')}
			<select class="select h-9 w-44 py-0 text-sm" bind:value={ig}>
				<option value="">Each audit's own</option>
				{#each feed.framework.implementation_groups as g (g.ref_id)}
					<option value={g.ref_id}>{g.name}</option>
				{/each}
			</select>
		</label>
		<label>
			{@render fieldLabel('Section')}
			<select class="select h-9 w-56 py-0 text-sm" bind:value={section}>
				<option value={null}>All sections</option>
				{#each feed.sections as s, i (s.id)}
					<option value={i}>{sectionLabel(i)}</option>
				{/each}
			</select>
		</label>
		<div>
			{@render fieldLabel('Metric')}
			<div class="flex h-9 overflow-hidden rounded-md border border-surface-300-700">
				{#each [['compliance', 'Compliance'], ['score', 'Score']] as [k, label] (k)}
					<button
						disabled={k === 'score' && !hasScores}
						title={k === 'score' && !hasScores ? 'No audit in this view records scores' : undefined}
						class="px-3 text-sm disabled:cursor-not-allowed disabled:opacity-40 {shownMetric === k
							? 'preset-filled-primary-500'
							: 'hover:bg-surface-100-900'}"
						onclick={() => (metric = k as Metric)}>{label}</button
					>
				{/each}
			</div>
		</div>
		<label>
			{@render fieldLabel('Branch average')}
			<select class="select h-9 w-52 py-0 text-sm" bind:value={agg}>
				{#each AGGREGATIONS as a (a.key)}<option value={a.key}>{a.label}</option>{/each}
			</select>
		</label>
		{#if isDummy}
			<div>
				{@render fieldLabel('Dummy organisation')}
				<div class="flex gap-1">
					<select
						class="select h-9 w-36 py-0 text-sm"
						aria-label="Dummy organisation size"
						bind:value={size}
						onchange={() => {
							selectedId = null;
							collapseTo(size === 'small' ? null : 2);
						}}
					>
						<option value="small">12 domains</option>
						<option value="medium">~60 domains</option>
						<option value="large">~200 domains</option>
					</select>
					<button
						type="button"
						class="btn-icon h-9 w-9 preset-tonal"
						title="Regenerate"
						aria-label="Regenerate"
						onclick={() => (seed = Math.floor(Math.random() * 1e6))}
						><i class="fa-solid fa-dice"></i></button
					>
				</div>
			</div>
		{/if}
	</div>

	{#if data.error}
		<div class="card preset-tonal-error p-4 text-sm">{data.error}</div>
	{:else}
		<div class="flex flex-col gap-4 lg:flex-row">
			<div class="min-w-0 flex-1 rounded-lg border border-surface-200-800 bg-surface-50-950">
				<div class="space-y-2 border-b border-surface-200-800 px-4 py-3">
					<div>
						<div class="text-sm font-semibold">{caption}</div>
						<div class="text-xs text-surface-600-400">
							{captionNotes}
						</div>
						{#if focusN}
							<div class="text-xs text-primary-700-300">
								Showing only the paths to the {weakest.length} weakest audited domains, ranked by their
								own audit{#if tooEarly.length}
									· {tooEarly.length} low-coverage audits are not ranked{/if}
							</div>
						{/if}
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<div class="relative">
							<input
								class="input h-8 w-56 py-0 text-sm"
								type="search"
								placeholder="Find a domain…"
								bind:value={query}
								onkeydown={(e) => e.key === 'Enter' && matches[0] && reveal(matches[0])}
							/>
							{#if matches.length}
								<ul
									class="absolute left-0 z-20 mt-1 w-80 overflow-hidden rounded-md border border-surface-200-800 bg-surface-50-950 shadow-lg"
								>
									{#each matches as m (m.id)}
										<li>
											<button
												class="w-full px-3 py-1.5 text-left hover:bg-surface-100-900"
												onclick={() => reveal(m)}
											>
												<div class="text-sm font-medium">{m.name}</div>
												<div class="truncate text-xs text-surface-500">{path(m)}</div>
											</button>
										</li>
									{/each}
								</ul>
							{/if}
						</div>
						<select class="select h-8 w-36 py-0 text-sm" bind:value={focusN} aria-label="Focus">
							<option value={0}>All domains</option>
							<option value={5}>5 weakest</option>
							<option value={10}>10 weakest</option>
							<option value={20}>20 weakest</option>
						</select>
						<select class="select h-8 w-32 py-0 text-sm" bind:value={mode} aria-label="View">
							<option value="auto">Auto view</option>
							<option value="tree">Tree</option>
							<option value="outline">Outline</option>
						</select>
						<label class="flex items-center gap-1.5 text-xs text-surface-600-400">
							<input type="checkbox" class="checkbox" bind:checked={hideEmpty} />
							Hide domains without audits
						</label>
						<div class="ml-auto flex gap-1">
							<button
								class="btn-icon h-8 w-8 preset-tonal"
								title="Expand all"
								aria-label="Expand all"
								onclick={() => collapseTo(null)}
								><i class="fa-solid fa-up-right-and-down-left-from-center"></i></button
							>
							<button
								class="btn-icon h-8 w-8 preset-tonal"
								title="Top level only"
								aria-label="Top level only"
								onclick={() => collapseTo(1)}
								><i class="fa-solid fa-down-left-and-up-right-to-center"></i></button
							>
						</div>
					</div>
				</div>
				{#if ringRoot}
					{#if outline}
						<RingOutline
							bind:this={outlineRef}
							root={ringRoot}
							collapsed={shownCollapsed}
							{only}
							locked={!!focusSet}
							{selectedId}
							{color}
							labelHeader="Domain"
							ownHeader="Own"
							branchHeader="Branch"
							height={TREE_HEIGHT}
							onselect={(id) => (selectedId = id)}
							ontoggle={toggle}
						/>
					{:else}
						<RingTree
							bind:this={treeRef}
							root={ringRoot}
							collapsed={shownCollapsed}
							{only}
							locked={!!focusSet}
							{selectedId}
							{color}
							{fitKey}
							height={TREE_HEIGHT}
							onselect={(id) => (selectedId = id)}
							ontoggle={toggle}
						/>
					{/if}
				{/if}
				<div
					class="flex flex-wrap items-center gap-x-5 gap-y-1 border-t border-surface-200-800 px-4 py-2 text-xs text-surface-600-400"
				>
					<span class="flex items-center gap-2">
						<svg width="22" height="22" viewBox="-14 -14 28 28" class="text-surface-800-200">
							<RingGlyph
								own={62}
								ownSegments={shownMetric === 'compliance'
									? [
											{ fraction: 0.45, color: complianceResultColorMap.compliant },
											{ fraction: 0.2, color: complianceResultColorMap.partially_compliant },
											{ fraction: 0.15, color: complianceResultColorMap.non_compliant }
										]
									: undefined}
								branch={70}
								{color}
								rOut={12}
								rIn={6.5}
								wOut={2.5}
								wIn={4}
							/>
						</svg>
						Inner: own audit{shownMetric === 'compliance'
							? ' (results as on the audit page)'
							: ' (audit score)'} · outer: whole branch, when sub-domains add audits
					</span>
					<span class="flex items-center gap-1.5">
						<span class="h-2 w-2 rounded-full" style="background: var(--color-error-500)"
						></span>&lt;40%
						<span class="ml-1 h-2 w-2 rounded-full" style="background: var(--color-warning-500)"
						></span>&lt;70%
						<span class="ml-1 h-2 w-2 rounded-full" style="background: var(--color-success-500)"
						></span>≥70%
					</span>
					<span
						>Dashed, faded, <span class="text-warning-600">◔</span>: under {MIN_PROGRESS}% progress
						or fewer than {MIN_ANSWERS} answers</span
					>
					<span class="ml-auto font-mono text-[11px] text-surface-500">
						{feed.folders.length} domains · {feed.audits.length} audits · {feedKb.toFixed(1)} KB
					</span>
				</div>
			</div>

			<aside class="w-full shrink-0 space-y-4 rounded-lg border border-surface-200-800 p-4 lg:w-96">
				{#if selected}
					<div>
						<h3 class="text-lg font-bold">{label(selected)}</h3>
						<p class="text-xs text-surface-600-400">
							{#if selected.audit}
								{selected.audit.name} · {statusLabel(selected.audit.status)}
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
						{#if selected.audit.progress !== null}
							<p class="text-xs text-surface-600-400">
								Progress on the audit page: {selected.audit.progress}%
							</p>
						{/if}
						{#if lowCoverage(selected)}
							<p class="text-xs text-warning-700-300">
								<span>◔</span> Low coverage. {coverageNote(selected)} with a dashed ring.
							</p>
						{/if}
					{/if}
					{#if branchAddsInfo(selected)}
						{@render statBlock(
							'Branch',
							selected.auditsInBranch ? selected.branch : null,
							undefined,
							branchVal(selected)
						)}
					{/if}

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
											<span class="flex-1 truncate">{label(c)}</span>
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

					{#if sectionBreakdown.length && filters.section === null}
						<div>
							<div class="mb-1 text-xs font-semibold uppercase tracking-wide text-surface-600-400">
								Branch by section, weakest first
							</div>
							<ul class="space-y-1">
								{#each sectionBreakdown as s (s.id)}
									<li>
										<button
											class="flex w-full items-center gap-2 rounded px-1 py-0.5 text-left text-xs hover:bg-surface-100-900"
											title="Filter the tree on this section"
											onclick={() => (section = s.index)}
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
	{/if}
</div>

<style>
	.picker :global(div.multiselect) {
		height: 2.25rem;
		min-height: 0;
		flex-wrap: nowrap;
		padding-block: 0;
	}
	.picker :global(ul.selected) {
		flex-wrap: nowrap;
		min-width: 0;
	}
</style>

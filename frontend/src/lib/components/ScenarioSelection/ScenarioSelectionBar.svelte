<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Popover } from '@skeletonlabs/skeleton-svelte';
	import { onMount } from 'svelte';
	import { m } from '#paraglide/messages.js';
	import { breadcrumbs } from '#lib/utils/breadcrumbs.js';
	import { FILTER_LABELS, filterLabel, optionLabel as labelFor } from './labels';
	import RelatedFilterOptions from './RelatedFilterOptions.svelte';
	import {
		SELECTION_FILTERS,
		SELECTION_PREFIX,
		hasSelection,
		isRelatedFilter,
		readSelection,
		recallSelection,
		rememberSelection,
		selectionParams,
		selectionToParams,
		type FacetOption,
		type ScenarioSelectionData,
		type SelectionFilter,
		type SelectionValues
	} from '#lib/utils/scenarioSelection.js';

	interface Props {
		riskAssessmentId: string;
		/** Null while loading or when the backend refused the selection. */
		selection: ScenarioSelectionData | null;
		/** Optional line under the bar, e.g. what the selection does to this view. */
		note?: string;
	}

	let { riskAssessmentId, selection, note }: Props = $props();

	const values: SelectionValues = $derived(readSelection(page.url.searchParams));
	const ignored = $derived(selection?.ignored ?? []);
	// Values the backend dropped (deleted objects) get their own warning chip.
	const applied = $derived(
		Object.fromEntries(
			SELECTION_FILTERS.map((name) => [
				name,
				(values[name] ?? []).filter(
					(v) => !ignored.some((stale) => stale.filter === name && stale.value === v)
				)
			])
		) as Record<SelectionFilter, string[]>
	);
	const scoped = $derived(SELECTION_FILTERS.some((name) => (values[name]?.length ?? 0) > 0));
	const toleranceSet = $derived((selection?.risk_tolerance ?? -1) >= 0);

	// Always shown as buttons; the others sit behind "More filters" until used.
	const PRIMARY_FILTERS: SelectionFilter[] = [
		'within_tolerance',
		'treatment',
		'current_level',
		'residual_level'
	];
	const SEARCH_THRESHOLD = 8;

	// Hover and open states stay in the primary hue: the bar is tinted once a
	// selection applies, and a neutral gray reads as a smudge on it. They are
	// lighter than an applied filter so a hovered button never looks applied.
	const HOVER_TINT = 'hover:bg-primary-500/10';
	const OPEN_TINT = 'bg-primary-500/15';
	const APPLIED = 'bg-primary-100 dark:bg-primary-900/50 ring-1 ring-inset';
	const APPLIED_RING =
		'ring-primary-300 dark:ring-primary-700 hover:ring-primary-500 dark:hover:ring-primary-400';
	const APPLIED_RING_OPEN = 'ring-primary-500 dark:ring-primary-400';
	const FOCUS_RING =
		'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500';
	const QUIET_BUTTON = `inline-flex items-center gap-1.5 h-8 px-3 rounded-full text-sm font-medium whitespace-nowrap text-primary-700 dark:text-primary-200 ${HOVER_TINT} ${FOCUS_RING}`;

	let openFilter: SelectionFilter | 'more' | null = $state(null);
	let query = $state('');
	let restored = $state(false);
	let copied = $state(false);
	// Off until the remembered selection (if any) is back in the URL, so the
	// empty URL seen on mount does not erase it first.
	let ready = $state(false);

	function optionLabel(name: SelectionFilter, value: string): string {
		return labelFor(name, value, selection);
	}

	// Related filters have no options here: they load theirs once opened.
	function options(name: SelectionFilter): FacetOption[] {
		return isRelatedFilter(name) ? [] : (selection?.facets?.[name] ?? []);
	}

	// Filters with nothing to pick in this assessment are left out, except
	// tolerance, which explains why it is unavailable.
	function available(name: SelectionFilter): boolean {
		if (name === 'within_tolerance' || applied[name].length > 0) return true;
		return isRelatedFilter(name)
			? (selection?.related_filters?.[name]?.has_options ?? false)
			: options(name).length > 0;
	}

	const buttonFilters = $derived(
		SELECTION_FILTERS.filter(
			(name) =>
				available(name) &&
				(PRIMARY_FILTERS.includes(name) || applied[name].length > 0 || openFilter === name)
		)
	);
	const moreFilters = $derived(
		SELECTION_FILTERS.filter((name) => available(name) && !buttonFilters.includes(name))
	);

	function setOpen(name: SelectionFilter | 'more', isOpen: boolean) {
		if (isOpen) {
			openFilter = name;
			query = '';
		} else if (openFilter === name) {
			openFilter = null;
		}
	}

	function summary(name: SelectionFilter): string {
		const labels = applied[name].map((v) => optionLabel(name, v));
		return labels.length <= 2 ? labels.join(', ') : `${labels[0]} +${labels.length - 1}`;
	}

	function matchingOptions(name: SelectionFilter): FacetOption[] {
		const q = query.trim().toLowerCase();
		if (!q) return options(name);
		return options(name).filter((o) =>
			(o.label ?? optionLabel(name, o.value)).toLowerCase().includes(q)
		);
	}

	function apply(next: SelectionValues) {
		const url = new URL(page.url.href);
		for (const key of [...url.searchParams.keys()]) {
			if (key.startsWith(SELECTION_PREFIX)) url.searchParams.delete(key);
		}
		for (const [key, value] of selectionToParams(next)) url.searchParams.append(key, value);
		copied = false;
		restored = false;
		goto(url, { replace: true, reset: false });
	}

	function toggle(name: SelectionFilter, value: string) {
		const current = values[name] ?? [];
		const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
		apply({ ...values, [name]: next });
	}

	function remove(name: SelectionFilter) {
		setOpen(name, false);
		apply({ ...values, [name]: [] });
	}

	function removeValue(name: string, value: string) {
		const key = name as SelectionFilter;
		apply({ ...values, [key]: (values[key] ?? []).filter((v) => v !== value) });
	}

	function clear() {
		openFilter = null;
		apply({});
	}

	async function copyLink() {
		try {
			await navigator.clipboard.writeText(page.url.href);
			copied = true;
		} catch {
			copied = false;
		}
	}

	onMount(() => {
		// A link carrying a selection always wins over the remembered one.
		const recalled = hasSelection(page.url.searchParams) ? null : recallSelection(riskAssessmentId);
		if (!recalled) {
			ready = true;
			return;
		}
		const url = new URL(page.url.href);
		for (const [key, value] of recalled) url.searchParams.append(key, value);
		restored = true;
		goto(url, { replace: true, reset: false }).finally(() => (ready = true));
	});

	$effect(() => {
		const params = selectionParams(page.url.searchParams);
		if (ready) rememberSelection(riskAssessmentId, params);
	});

	// Keep this page's crumb on the current selection, so coming back through
	// the breadcrumb lands on the same view.
	$effect(() => {
		const href = page.url.pathname + page.url.search;
		breadcrumbs.update((crumbs) => {
			const last = crumbs[crumbs.length - 1];
			if (!last || last.href?.split('?')[0] !== page.url.pathname || last.href === href)
				return crumbs;
			return [...crumbs.slice(0, -1), { ...last, href }];
		});
	});
</script>

{#snippet optionRow(name: SelectionFilter, option: FacetOption)}
	{@const checked = (values[name] ?? []).includes(option.value)}
	<label
		class="flex items-center gap-2.5 min-h-10 px-2.5 rounded-md text-sm cursor-pointer hover:bg-surface-100-900 {option.count ===
			0 && !checked
			? 'text-surface-500'
			: ''}"
		data-testid="selection-option"
	>
		<input type="checkbox" class="checkbox" {checked} onchange={() => toggle(name, option.value)} />
		<span class="grow">{option.label ?? optionLabel(name, option.value)}</span>
		<span class="tabular-nums text-surface-500">{option.count}</span>
	</label>
{/snippet}

<section
	aria-label={m.scenarioSelection()}
	class="rounded-lg border overflow-hidden {scoped
		? 'border-primary-300 dark:border-primary-700 bg-primary-50/60 dark:bg-primary-950/30'
		: 'border-surface-200-800 bg-surface-50-950'} {restored && scoped
		? 'border-2 border-primary-500'
		: ''}"
	data-testid="scenario-selection-bar"
>
	{#if restored && scoped}
		<div
			class="flex flex-wrap items-center gap-3 px-4 py-2 bg-primary-500 text-white text-sm"
			data-testid="selection-restored"
		>
			<i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i>
			<span>{m.selectionRestored()}</span>
			<button
				type="button"
				class="ml-auto btn btn-sm border border-white/60 text-white"
				onclick={clear}
			>
				{m.startFromAllScenarios()}
			</button>
		</div>
	{/if}
	<div class="flex flex-wrap items-start gap-x-4 gap-y-2 px-4 py-3">
		<div class="flex items-center gap-2 h-8 font-semibold text-primary-700 dark:text-primary-200">
			<i class="fa-solid fa-filter" aria-hidden="true"></i>
			{m.scenarioSelection()}
		</div>
		<div class="flex flex-wrap items-center gap-1.5 flex-1 basis-xl min-w-0">
			{#each buttonFilters as name (name)}
				{@const isActive = applied[name].length > 0}
				{@const locked = name === 'within_tolerance' && !toleranceSet}
				{@const isOpen = openFilter === name}
				<span
					class="inline-flex items-center h-8 rounded-full text-sm transition-colors {isActive
						? `${APPLIED} ${isOpen ? APPLIED_RING_OPEN : APPLIED_RING}`
						: `${HOVER_TINT} ${isOpen ? OPEN_TINT : ''}`}"
					data-testid="selection-filter-{name}"
				>
					<Popover
						open={isOpen}
						onOpenChange={(e) => setOpen(name, e.open)}
						positioning={{ placement: 'bottom-start' }}
						autoFocus={false}
						closeOnInteractOutside={true}
					>
						<Popover.Trigger
							class="inline-flex items-center gap-1.5 h-8 pl-3 {isActive
								? 'pr-1.5'
								: 'pr-2.5'} rounded-full whitespace-nowrap {FOCUS_RING}"
							title={isActive
								? applied[name].map((v) => optionLabel(name, v)).join(', ')
								: undefined}
						>
							{#if isActive}
								<span class="text-primary-800/80 dark:text-primary-200/80"
									>{m.selectionFilterLabel({ filter: FILTER_LABELS[name]() })}</span
								>
								<span class="font-semibold text-primary-900 dark:text-primary-50"
									>{summary(name)}</span
								>
							{:else}
								<span class={locked ? 'text-surface-500' : 'text-surface-800-200'}
									>{FILTER_LABELS[name]()}</span
								>
								<i
									class="fa-solid {locked
										? 'fa-lock'
										: 'fa-chevron-down'} text-[10px] text-surface-500 transition-transform {isOpen &&
									!locked
										? 'rotate-180'
										: ''}"
									aria-hidden="true"
								></i>
							{/if}
						</Popover.Trigger>
						<Popover.Positioner class="z-50!">
							<Popover.Content
								class="card p-1.5 bg-surface-50-950 w-72 shadow-lg border border-surface-200-800"
							>
								{#if isOpen}
									{#if locked}
										<p class="px-2.5 py-2 text-sm text-surface-600-400">
											{m.noRiskToleranceDefined()}
											<a class="anchor" href="/risk-assessments/{riskAssessmentId}/edit"
												>{m.setRiskTolerance()}</a
											>
										</p>
									{:else}
										{#if isRelatedFilter(name)}
											<RelatedFilterOptions {riskAssessmentId} {name}>
												{#snippet option(item)}
													{@render optionRow(name, item)}
												{/snippet}
											</RelatedFilterOptions>
										{:else}
											{#if options(name).length > SEARCH_THRESHOLD}
												<label class="block px-1 pt-1 pb-1.5">
													<span class="sr-only">{m.search()}</span>
													<input
														type="search"
														class="input text-sm"
														placeholder={m.searchPlaceholder()}
														bind:value={query}
														{@attach (el) => el.focus()}
													/>
												</label>
											{/if}
											<ul class="max-h-72 overflow-y-auto">
												{#each matchingOptions(name) as option (option.value)}
													<li>{@render optionRow(name, option)}</li>
												{:else}
													<li class="px-2.5 py-2 text-sm text-surface-500">{m.noResults()}</li>
												{/each}
											</ul>
										{/if}
										{#if isActive}
											<div class="flex justify-end pt-1.5 mt-1 border-t border-surface-200-800">
												<button type="button" class={QUIET_BUTTON} onclick={() => remove(name)}>
													{m.clearFilterValues()}
												</button>
											</div>
										{/if}
									{/if}
								{/if}
							</Popover.Content>
						</Popover.Positioner>
					</Popover>
					{#if isActive}
						<button
							type="button"
							class="size-6 mr-1 rounded-full inline-flex items-center justify-center text-xs text-primary-700 dark:text-primary-200 hover:bg-primary-200 dark:hover:bg-primary-800 {FOCUS_RING}"
							aria-label={m.removeSelectionFilter({ filter: FILTER_LABELS[name]() })}
							onclick={() => remove(name)}
						>
							<i class="fa-solid fa-xmark" aria-hidden="true"></i>
						</button>
					{/if}
				</span>
			{/each}
			{#if moreFilters.length > 0}
				<Popover
					open={openFilter === 'more'}
					onOpenChange={(e) => setOpen('more', e.open)}
					positioning={{ placement: 'bottom-start' }}
					autoFocus={false}
					closeOnInteractOutside={true}
				>
					<Popover.Trigger
						class="{QUIET_BUTTON} {openFilter === 'more' ? OPEN_TINT : ''}"
						data-testid="selection-more-filters"
					>
						<i class="fa-solid fa-plus text-[10px]" aria-hidden="true"></i>
						{m.moreFilters()}
					</Popover.Trigger>
					<Popover.Positioner class="z-50!">
						<Popover.Content
							class="card p-1.5 bg-surface-50-950 w-60 shadow-lg border border-surface-200-800"
						>
							{#if openFilter === 'more'}
								<ul>
									{#each moreFilters as name (name)}
										<li>
											<button
												type="button"
												class="w-full flex items-center justify-between gap-2 min-h-10 px-2.5 rounded-md text-sm text-left hover:bg-surface-100-900"
												onclick={() => setOpen(name, true)}
												data-testid="selection-more-{name}"
											>
												{FILTER_LABELS[name]()}
											</button>
										</li>
									{/each}
								</ul>
							{/if}
						</Popover.Content>
					</Popover.Positioner>
				</Popover>
			{/if}
			{#each ignored as stale (`${stale.filter}:${stale.value}`)}
				<span
					class="inline-flex items-center gap-2 h-8 rounded-full ring-1 ring-inset ring-warning-500 bg-warning-50 text-warning-900 dark:bg-warning-950/40 dark:text-warning-200 pl-3 pr-1 text-sm"
					data-testid="selection-ignored"
				>
					<i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>
					{m.selectionFilterLabel({ filter: filterLabel(stale.filter) })}
					{m.selectionValueDeleted()}
					<button
						type="button"
						class="px-1"
						aria-label={m.removeSelectionFilter({ filter: filterLabel(stale.filter) })}
						onclick={() => removeValue(stale.filter, stale.value)}
					>
						<i class="fa-solid fa-xmark" aria-hidden="true"></i>
					</button>
				</span>
			{/each}
		</div>
		<div class="flex items-center gap-1 h-8 ml-auto shrink-0">
			{#if selection}
				<span class="text-sm whitespace-nowrap tabular-nums pr-2" data-testid="selection-count">
					{scoped
						? m.scenarioSelectionCount({ count: selection.count, total: selection.total })
						: m.scenarioCount({ count: selection.total })}
				</span>
			{/if}
			{#if scoped}
				<button type="button" class={QUIET_BUTTON} onclick={copyLink}>
					<i class="fa-solid {copied ? 'fa-check' : 'fa-link'} text-xs" aria-hidden="true"></i>
					{copied ? m.selectionLinkCopied() : m.copySelectionLink()}
				</button>
				<button type="button" class={QUIET_BUTTON} onclick={clear} data-testid="selection-clear">
					<i class="fa-solid fa-xmark text-xs" aria-hidden="true"></i>
					{m.clearSelection()}
				</button>
			{/if}
		</div>
	</div>
	{#if scoped && selection?.count === 0}
		<p
			class="px-4 pb-3 -mt-1 text-sm font-semibold text-warning-800 dark:text-warning-200"
			role="status"
			data-testid="selection-empty"
		>
			{m.noScenarioMatchesSelection()}
		</p>
	{:else if note && scoped}
		<p class="px-4 pb-3 -mt-1 text-sm text-surface-600-400">{note}</p>
	{/if}
</section>

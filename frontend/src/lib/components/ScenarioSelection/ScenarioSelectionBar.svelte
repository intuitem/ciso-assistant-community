<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Popover } from '@skeletonlabs/skeleton-svelte';
	import { onMount } from 'svelte';
	import { m } from '#paraglide/messages.js';
	import { breadcrumbs } from '#lib/utils/breadcrumbs.js';
	import { FILTER_LABELS, filterLabel, optionLabel as labelFor } from './labels';
	import {
		SELECTION_FILTERS,
		SELECTION_PREFIX,
		hasSelection,
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

	function options(name: SelectionFilter): FacetOption[] {
		return selection?.facets?.[name] ?? [];
	}

	// Filters with nothing to pick in this assessment are left out, except
	// tolerance, which explains why it is unavailable.
	function available(name: SelectionFilter): boolean {
		return name === 'within_tolerance' || applied[name].length > 0 || options(name).length > 0;
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

<section
	aria-label={m.scenarioSelection()}
	class="rounded-lg border overflow-hidden {scoped
		? 'border-primary-300 bg-primary-50/60 dark:bg-primary-950/30'
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
	<div class="flex flex-wrap items-center gap-3 px-4 py-3">
		<div class="flex items-center gap-2 font-semibold text-primary-700 dark:text-primary-300">
			<i class="fa-solid fa-filter" aria-hidden="true"></i>
			{m.scenarioSelection()}
		</div>
		<div class="flex flex-wrap items-center gap-2 flex-1 basis-xl min-w-0">
			{#each buttonFilters as name (name)}
				{@const isActive = applied[name].length > 0}
				{@const locked = name === 'within_tolerance' && !toleranceSet}
				<span
					class="inline-flex items-stretch rounded-full border overflow-hidden {isActive
						? 'border-primary-300 bg-primary-50 dark:bg-primary-900/40'
						: 'border-surface-300-700 bg-surface-50-950'}"
					data-testid="selection-filter-{name}"
				>
					<Popover
						open={openFilter === name}
						onOpenChange={(e) => setOpen(name, e.open)}
						positioning={{ placement: 'bottom-start' }}
						autoFocus={false}
						closeOnInteractOutside={true}
					>
						<Popover.Trigger
							class="inline-flex items-center gap-1.5 min-h-8 pl-3 pr-2.5 text-sm whitespace-nowrap hover:bg-primary-100/60 dark:hover:bg-primary-900/60"
							title={isActive
								? applied[name].map((v) => optionLabel(name, v)).join(', ')
								: undefined}
						>
							{#if isActive}
								<span class="text-surface-600-400"
									>{m.selectionFilterLabel({ filter: FILTER_LABELS[name]() })}</span
								>
								<strong>{summary(name)}</strong>
							{:else}
								<span class="font-medium {locked ? 'text-surface-500' : ''}"
									>{FILTER_LABELS[name]()}</span
								>
							{/if}
							<i
								class="fa-solid {locked
									? 'fa-lock'
									: 'fa-chevron-down'} text-[10px] text-surface-500"
								aria-hidden="true"
							></i>
						</Popover.Trigger>
						<Popover.Positioner class="z-50!">
							<Popover.Content
								class="card p-1.5 bg-surface-50-950 w-72 shadow-lg border border-surface-200-800"
							>
								{#if openFilter === name}
									{#if locked}
										<p class="px-2.5 py-2 text-sm text-surface-600-400">
											{m.noRiskToleranceDefined()}
											<a class="anchor" href="/risk-assessments/{riskAssessmentId}/edit"
												>{m.setRiskTolerance()}</a
											>
										</p>
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
												{@const checked = (values[name] ?? []).includes(option.value)}
												<li>
													<label
														class="flex items-center gap-2.5 min-h-10 px-2.5 rounded-md text-sm cursor-pointer hover:bg-surface-100-900 {option.count ===
															0 && !checked
															? 'text-surface-500'
															: ''}"
														data-testid="selection-option"
													>
														<input
															type="checkbox"
															class="checkbox"
															{checked}
															onchange={() => toggle(name, option.value)}
														/>
														<span class="grow"
															>{option.label ?? optionLabel(name, option.value)}</span
														>
														<span class="tabular-nums text-surface-500">{option.count}</span>
													</label>
												</li>
											{:else}
												<li class="px-2.5 py-2 text-sm text-surface-500">{m.noResults()}</li>
											{/each}
										</ul>
										{#if isActive}
											<div class="flex justify-end pt-1.5 mt-1 border-t border-surface-200-800">
												<button
													type="button"
													class="btn btn-sm underline underline-offset-4"
													onclick={() => remove(name)}
												>
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
							class="px-2.5 border-l border-primary-300 text-surface-500 hover:text-error-600"
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
						class="inline-flex items-center gap-1.5 min-h-8 px-3 rounded-full border border-dashed border-primary-400 text-primary-700 dark:text-primary-300 font-semibold text-sm whitespace-nowrap"
						data-testid="selection-more-filters"
					>
						{m.moreFilters()}
						<i class="fa-solid fa-chevron-down text-[10px]" aria-hidden="true"></i>
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
												<span>{FILTER_LABELS[name]()}</span>
												<span class="text-xs text-surface-500 tabular-nums"
													>{options(name).length}</span
												>
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
					class="inline-flex items-center gap-2 rounded-full border border-warning-500 bg-warning-50 text-warning-900 dark:bg-warning-950/40 dark:text-warning-200 pl-3 pr-1 py-1 text-sm"
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
		<div class="flex items-center gap-1 ml-auto shrink-0">
			{#if selection}
				<span class="text-sm whitespace-nowrap tabular-nums pr-2" data-testid="selection-count">
					{scoped
						? m.scenarioSelectionCount({ count: selection.count, total: selection.total })
						: m.scenarioCount({ count: selection.total })}
				</span>
			{/if}
			{#if scoped}
				<button type="button" class="btn btn-sm preset-tonal-surface" onclick={copyLink}>
					<i class="fa-solid fa-link mr-1" aria-hidden="true"></i>
					{copied ? m.selectionLinkCopied() : m.copySelectionLink()}
				</button>
				<button
					type="button"
					class="btn btn-sm underline underline-offset-4"
					onclick={clear}
					data-testid="selection-clear"
				>
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
	{#if scoped && selection}
		<div class="h-0.5 bg-primary-100 dark:bg-primary-900/50" aria-hidden="true">
			<div
				class="h-0.5 bg-primary-500 transition-[width]"
				style="width: {selection.total
					? Math.round((selection.count / selection.total) * 100)
					: 0}%"
			></div>
		</div>
	{/if}
</section>

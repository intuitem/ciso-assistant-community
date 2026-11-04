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
	const active = $derived(SELECTION_FILTERS.filter((name) => applied[name].length > 0));
	const scoped = $derived(SELECTION_FILTERS.some((name) => (values[name]?.length ?? 0) > 0));
	const toleranceSet = $derived((selection?.risk_tolerance ?? -1) >= 0);

	let open = $state(false);
	let field: SelectionFilter | null = $state(null);
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

	// Filters with nothing to pick in this assessment stay out of the menu,
	// except tolerance, which explains why it is unavailable.
	const menuFilters = $derived(
		SELECTION_FILTERS.filter(
			(name) => name === 'within_tolerance' || applied[name].length > 0 || options(name).length > 0
		)
	);

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
		apply({ ...values, [name]: [] });
	}

	function removeValue(name: string, value: string) {
		const key = name as SelectionFilter;
		apply({ ...values, [key]: (values[key] ?? []).filter((v) => v !== value) });
	}

	function clear() {
		open = false;
		apply({});
	}

	function edit(name: SelectionFilter) {
		field = name;
		open = true;
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
		<div class="flex flex-wrap items-center gap-2 grow basis-96 min-w-0">
			{#if !scoped}
				<span class="text-surface-600-400">{m.allScenarios()}</span>
			{/if}
			{#each active as name (name)}
				<span
					class="inline-flex items-stretch rounded-full border border-primary-200 bg-surface-50-950 overflow-hidden"
					data-testid="selection-chip-{name}"
				>
					<button
						type="button"
						class="pl-3 pr-1 py-1 min-h-8 text-sm hover:bg-primary-50 dark:hover:bg-primary-900/40"
						onclick={() => edit(name)}
					>
						<span class="text-surface-600-400"
							>{m.selectionFilterLabel({ filter: FILTER_LABELS[name]() })}</span
						>
						<strong>{applied[name].map((v) => optionLabel(name, v)).join(', ')}</strong>
					</button>
					<button
						type="button"
						class="px-2 text-surface-500 hover:text-error-600"
						aria-label={m.removeSelectionFilter({ filter: FILTER_LABELS[name]() })}
						onclick={() => remove(name)}
					>
						<i class="fa-solid fa-xmark" aria-hidden="true"></i>
					</button>
				</span>
			{/each}
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
			<Popover
				{open}
				onOpenChange={(e) => {
					open = e.open;
					if (!e.open) field = null;
				}}
				positioning={{ placement: 'bottom-start' }}
				autoFocus={false}
				closeOnInteractOutside={true}
			>
				<Popover.Trigger
					class="inline-flex items-center gap-1 min-h-8 px-3 rounded-full border border-dashed border-primary-400 text-primary-700 dark:text-primary-300 font-semibold text-sm"
					data-testid="selection-add-filter"
				>
					<i class="fa-solid fa-plus" aria-hidden="true"></i>
					{m.addSelectionFilter()}
				</Popover.Trigger>
				<Popover.Positioner class="z-50!">
					<Popover.Content
						class="card p-1.5 bg-surface-50-950 w-80 shadow-lg border border-surface-200-800"
					>
						{#if open && field === null}
							<p
								class="px-2.5 pt-2 pb-1.5 text-xs font-semibold uppercase tracking-wide text-surface-500"
							>
								{m.filterScenariosBy()}
							</p>
							<ul>
								{#each menuFilters as name (name)}
									{@const disabled = name === 'within_tolerance' && !toleranceSet}
									<li>
										{#if disabled}
											<div class="px-2.5 py-2 rounded-md bg-surface-100-900 text-sm">
												<div class="flex justify-between text-surface-500">
													<span>{FILTER_LABELS[name]()}</span>
													<i class="fa-solid fa-lock text-xs" aria-hidden="true"></i>
												</div>
												<p class="text-xs text-surface-600-400 mt-1">
													{m.noRiskToleranceDefined()}
													<a class="anchor" href="/risk-assessments/{riskAssessmentId}/edit"
														>{m.setRiskTolerance()}</a
													>
												</p>
											</div>
										{:else}
											<button
												type="button"
												class="w-full flex items-center justify-between gap-2 min-h-10 px-2.5 rounded-md text-sm text-left hover:bg-surface-100-900"
												onclick={() => (field = name)}
												data-testid="selection-field-{name}"
											>
												<span>{FILTER_LABELS[name]()}</span>
												<span
													class="flex items-center gap-1.5 text-xs font-semibold text-primary-600 truncate"
												>
													{applied[name].map((v) => optionLabel(name, v)).join(', ')}
													<i class="fa-solid fa-chevron-right text-surface-400" aria-hidden="true"
													></i>
												</span>
											</button>
										{/if}
									</li>
								{/each}
							</ul>
						{:else if open && field !== null}
							{@const current = field}
							<div class="flex items-center gap-1 pb-1.5 mb-1 border-b border-surface-200-800">
								<button
									type="button"
									class="btn-icon btn-icon-sm"
									aria-label={m.back()}
									onclick={() => (field = null)}
								>
									<i class="fa-solid fa-chevron-left" aria-hidden="true"></i>
								</button>
								<strong class="grow text-sm">{FILTER_LABELS[current]()}</strong>
								<span class="text-xs text-surface-500 pr-2">{m.riskScenarios()}</span>
							</div>
							<ul class="max-h-72 overflow-y-auto">
								{#each options(current) as option (option.value)}
									{@const checked = (values[current] ?? []).includes(option.value)}
									<li>
										<button
											type="button"
											role="checkbox"
											aria-checked={checked}
											class="w-full flex items-center gap-2.5 min-h-10 px-2.5 rounded-md text-sm text-left hover:bg-surface-100-900 {option.count ===
												0 && !checked
												? 'text-surface-500'
												: ''}"
											onclick={() => toggle(current, option.value)}
											data-testid="selection-option"
										>
											<span
												class="size-4.5 shrink-0 rounded border-[1.5px] flex items-center justify-center {checked
													? 'bg-primary-500 border-primary-500 text-white'
													: 'border-surface-400'}"
											>
												{#if checked}<i class="fa-solid fa-check text-[10px]" aria-hidden="true"
													></i>{/if}
											</span>
											<span class="grow">{option.label ?? optionLabel(current, option.value)}</span>
											<span class="tabular-nums text-surface-500">{option.count}</span>
										</button>
									</li>
								{:else}
									<li class="px-2.5 py-2 text-sm text-surface-500">--</li>
								{/each}
							</ul>
							<div class="flex justify-end pt-1.5 mt-1 border-t border-surface-200-800">
								<button
									type="button"
									class="btn btn-sm preset-filled-primary-500"
									onclick={() => {
										open = false;
										field = null;
									}}
								>
									{m.done()}
								</button>
							</div>
						{/if}
					</Popover.Content>
				</Popover.Positioner>
			</Popover>
		</div>
		<div class="flex flex-wrap items-center gap-3 ml-auto">
			{#if selection}
				<div class="flex flex-col gap-1 min-w-36" data-testid="selection-count">
					<span class="text-sm">
						{scoped
							? m.scenarioSelectionCount({ count: selection.count, total: selection.total })
							: m.scenarioCount({ count: selection.total })}
					</span>
					{#if scoped}
						<span class="block h-1 rounded bg-surface-200-800 overflow-hidden">
							<span
								class="block h-1 bg-primary-500"
								style="width: {selection.total
									? Math.round((selection.count / selection.total) * 100)
									: 0}%"
							></span>
						</span>
					{/if}
				</div>
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
</section>

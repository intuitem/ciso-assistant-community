<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { fetchAllPages } from '$lib/utils/pagination';
	import type { CacheLock } from '$lib/utils/types';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import * as m from '$paraglide/messages';

	interface Option {
		label: string;
		value: string | number;
		group?: string;
		groupsList?: string[];
		translatedLabel?: string;
	}

	interface NestedGroup {
		[key: string]: {
			options: Option[];
			subGroups: NestedGroup;
			flatOptions: Option[];
		};
	}

	interface Props {
		form: SuperForm<Record<string, unknown>, any>;
		field: string;
		label?: string;
		helpText?: string;
		optionsEndpoint: string;
		optionsLabelField?: string;
		groupBy?: { field: string; path?: string[] }[] | string;
		cacheLock?: CacheLock;
		cachedValue?: (string | number)[] | undefined;
		translateOptions?: boolean;
		disabled?: boolean;
		mandatory?: boolean;
		showGroupHeaders?: boolean;
		collapsibleGroups?: boolean;
		defaultCollapsed?: boolean;
	}

	let {
		form,
		field,
		label,
		helpText,
		optionsEndpoint,
		optionsLabelField = 'name',
		groupBy = '',
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x: any) => x
		},
		cachedValue = $bindable(),
		translateOptions = true,
		disabled = false,
		mandatory = false,
		showGroupHeaders = true,
		collapsibleGroups = true,
		defaultCollapsed = true
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, field);

	let options: Option[] = $state([]);
	let nestedGroups: NestedGroup = $state({});
	let collapsedGroups: Set<string> = $state(new Set());
	let selected: (string | number)[] = $state([]);
	let selectedSet = $derived(new Set(selected));
	let isLoading = $state(false);

	function attachFlatOptions(nested: NestedGroup): void {
		Object.values(nested).forEach((group) => {
			attachFlatOptions(group.subGroups);
			group.flatOptions = group.options.concat(
				...Object.values(group.subGroups).map((sub) => sub.flatOptions)
			);
		});
	}

	function createNestedGroups(opts: Option[]): NestedGroup {
		if (!groupBy) {
			const nested: NestedGroup = { All: { options: opts, subGroups: {}, flatOptions: [] } };
			attachFlatOptions(nested);
			return nested;
		}

		const nested: NestedGroup = {};

		opts.forEach((option) => {
			const groupsList = option.groupsList || [];
			let currentLevel = nested;

			// Navigate/create the nested structure
			groupsList.forEach((group, index) => {
				if (!currentLevel[group]) {
					currentLevel[group] = { options: [], subGroups: {}, flatOptions: [] };
				}

				// If this is the last level, add the option
				if (index === groupsList.length - 1) {
					currentLevel[group].options.push(option);
				}

				// Move to next level
				currentLevel = currentLevel[group].subGroups;
			});

			// If no groups, add to root
			if (groupsList.length === 0) {
				if (!nested['Other']) {
					nested['Other'] = { options: [], subGroups: {}, flatOptions: [] };
				}
				nested['Other'].options.push(option);
			}
		});

		attachFlatOptions(nested);
		return nested;
	}

	function initializeCollapsedGroups(nested: NestedGroup, prefix = ''): Set<string> {
		if (!collapsibleGroups || !defaultCollapsed) {
			return new Set();
		}

		const collapsed = new Set<string>();

		function traverse(groups: NestedGroup, currentPrefix: string) {
			Object.keys(groups).forEach((key) => {
				const fullPath = currentPrefix ? `${currentPrefix}>${key}` : key;
				const hasSelection = groups[key].flatOptions.some((opt) => selectedSet.has(opt.value));
				if (!hasSelection) {
					collapsed.add(fullPath);
				}

				if (groups[key].subGroups && Object.keys(groups[key].subGroups).length > 0) {
					traverse(groups[key].subGroups, fullPath);
				}
			});
		}

		traverse(nested, prefix);
		return collapsed;
	}

	// fetch options
	async function fetchOptions() {
		isLoading = true;
		try {
			if ($value) {
				selected = Array.isArray($value) ? $value : [$value];
			}

			// fetchAllPages pages by explicit offset: the backend's `next`
			// links are backend-relative ("/api/...") and do not resolve
			// against the frontend origin this component fetches from.
			const collected = await fetchAllPages(fetch, `/${optionsEndpoint}`);
			if (collected.length) {
				options = collected.map((option: any) => {
					const label = option[optionsLabelField] ?? '--';
					const groupsList = Array.isArray(groupBy)
						? groupBy
								.map((group) => {
									let grp = option[group.field];
									if (group.path) {
										for (const p of group.path) {
											grp = grp?.[p];
										}
									}
									return grp;
								})
								.filter(Boolean)
						: groupBy
							? [option[groupBy]].filter(Boolean)
							: [];

					return {
						label,
						value: option.id,
						groupsList,
						translatedLabel: translateOptions ? safeTranslate(label) : label
					};
				});

				nestedGroups = createNestedGroups(options);

				if (collapsibleGroups && defaultCollapsed) {
					collapsedGroups = initializeCollapsedGroups(nestedGroups);
				}

				const validValues = new Set(options.map((o) => o.value));
				const reconciled = selected.filter((v) => validValues.has(v));
				if (reconciled.length !== selected.length) {
					selected = reconciled;
					$value = selected;
					cachedValue = selected;
				}
			}
		} catch (err) {
			console.error('Error fetching options', err);
		} finally {
			isLoading = false;
		}
	}

	function toggle(val: string | number) {
		if (selectedSet.has(val)) {
			selected = selected.filter((v) => v !== val);
		} else {
			selected = [...selected, val];
		}
		$value = selected;
		cacheLock.resolve(selected);
		cachedValue = selected;
	}

	function toggleGroup(groupPath: string) {
		if (!collapsibleGroups) return;

		if (collapsedGroups.has(groupPath)) {
			collapsedGroups.delete(groupPath);
		} else {
			collapsedGroups.add(groupPath);
		}
		collapsedGroups = new Set(collapsedGroups);
	}

	function selectAllInGroup(group: { flatOptions: Option[] }) {
		const groupValues = group.flatOptions.map((opt) => opt.value);
		const allSelected = groupValues.every((val) => selectedSet.has(val));

		if (allSelected) {
			const groupValuesSet = new Set(groupValues);
			selected = selected.filter((val) => !groupValuesSet.has(val));
		} else {
			selected = [...new Set([...selected, ...groupValues])];
		}

		$value = selected;
		cacheLock.resolve(selected);
		cachedValue = selected;
	}

	function getGroupSelectionState(group: { flatOptions: Option[] }) {
		const groupValues = group.flatOptions.map((opt) => opt.value);
		const selectedCount = groupValues.filter((val) => selectedSet.has(val)).length;

		if (selectedCount === 0) return 'none';
		if (selectedCount === groupValues.length) return 'all';
		return 'partial';
	}
	export function applyPreset(values: (string | number)[]): void {
		const validValues = new Set(options.map((o) => o.value));
		selected = values.filter((v) => validValues.has(v));
		$value = selected;
		cacheLock.resolve(selected);
		cachedValue = selected;
	}

	onMount(async () => {
		await fetchOptions();
		const cacheResult = await cacheLock.promise;
		if (cacheResult?.length) {
			selected = cacheResult;
			$value = selected;
			cachedValue = selected;
		} else if (cachedValue?.length) {
			selected = cachedValue;
			$value = selected;
		} else {
			return;
		}
		if (collapsibleGroups && defaultCollapsed) {
			collapsedGroups = initializeCollapsedGroups(nestedGroups);
		}
	});

	onDestroy(() => {
		cacheLock.resolve(selected);
	});
</script>

{#snippet renderNestedGroups(groups, depth, pathPrefix)}
	{#each Object.entries(groups) as [groupName, group]}
		{@const currentPath = pathPrefix ? `${pathPrefix}>${groupName}` : groupName}
		{@const hasSubGroups = Object.keys(group.subGroups).length > 0}
		{@const hasDirectOptions = group.options.length > 0}
		{@const isCollapsed = collapsedGroups.has(currentPath)}
		{@const totalOptions = group.flatOptions.length}
		{@const selectionState = showGroupHeaders && groupBy ? getGroupSelectionState(group) : 'none'}

		<div class="border border-surface-200-800 rounded-lg" style="margin-left: {depth * 20}px;">
			{#if showGroupHeaders && groupBy}
				<div
					class="px-3 py-2 border-b border-surface-200-800 flex items-center justify-between"
					class:bg-surface-50-950={depth === 0}
					class:bg-surface-100-900={depth === 1}
					class:bg-surface-200-800={depth >= 2}
				>
					<div class="flex items-center gap-2">
						{#if collapsibleGroups}
							<button
								type="button"
								aria-label="Toggle Group"
								class="text-surface-600-400 hover:text-surface-700-300 transition-transform duration-200"
								class:rotate-90={!isCollapsed}
								onclick={() => toggleGroup(currentPath)}
							>
								<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 111.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						{/if}
						<h3 class="text-sm font-medium text-surface-700-300" class:font-bold={depth === 0}>
							{safeTranslate(groupName)}
						</h3>
						<span class="text-xs text-surface-600-400">({totalOptions})</span>
					</div>

					<button
						type="button"
						class="text-xs px-2 py-1 rounded border border-surface-300-700 hover:bg-surface-100-900 transition-colors"
						class:preset-tonal-primary={selectionState === 'all'}
						class:preset-tonal-secondary={selectionState === 'partial'}
						onclick={() => selectAllInGroup(group)}
						{disabled}
					>
						{#if selectionState === 'all'}
							{m.deselectAll()}
						{:else}
							{m.selectAll()}
						{/if}
					</button>
				</div>
			{/if}

			{#if !collapsibleGroups || !isCollapsed}
				<!-- Direct options in this group -->
				{#if hasDirectOptions}
					<div class="p-3 space-y-2">
						{#each group.options as opt}
							<label
								class="flex items-center gap-2 hover:bg-surface-50-950 p-1 rounded transition-colors"
							>
								<input
									type="checkbox"
									value={opt.value}
									checked={selectedSet.has(opt.value)}
									onchange={() => toggle(opt.value)}
									{disabled}
									class="rounded border-surface-300-700 text-blue-600 focus:ring-blue-500"
								/>
								<span class="text-sm">{opt.translatedLabel ?? opt.label}</span>
							</label>
						{/each}
					</div>
				{/if}

				<!-- Nested subgroups -->
				{#if hasSubGroups}
					<div class="py-2 px-1 space-y-2">
						{@render renderNestedGroups(group.subGroups, depth + 1, currentPath)}
					</div>
				{/if}
			{/if}
		</div>
	{/each}
{/snippet}

<div class="space-y-4">
	{#if label}
		<span class="text-sm font-semibold">{label}{mandatory ? ' *' : ''}</span>
	{/if}

	{#if $errors && $errors.length > 0}
		<div>
			{#each $errors as error}
				<p class="text-error-500 text-xs">{error}</p>
			{/each}
		</div>
	{/if}

	{#if isLoading}
		<svg
			class="animate-spin h-5 w-5 text-primary-500 loading-spinner"
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			data-testid="loading-spinner"
		>
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
			></circle>
			<path
				class="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			></path>
		</svg>
	{:else}
		<div class="space-y-3">
			{@render renderNestedGroups(nestedGroups, 0, '')}
		</div>
	{/if}

	{#if helpText}
		<p class="text-sm text-surface-600-400">{helpText}</p>
	{/if}

	{#each selected as val}
		<input type="hidden" name={field} value={val} />
	{/each}
</div>

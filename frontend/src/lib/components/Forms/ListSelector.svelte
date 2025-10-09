<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
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
	let isLoading = $state(false);

	// Helper function to create nested structure from groupsList
	function createNestedGroups(opts: Option[]): NestedGroup {
		if (!groupBy) {
			return {
				All: {
					options: opts,
					subGroups: {}
				}
			};
		}

		const nested: NestedGroup = {};

		opts.forEach((option) => {
			const groupsList = option.groupsList || [];
			let currentLevel = nested;
			let pathSoFar = '';

			// Navigate/create the nested structure
			groupsList.forEach((group, index) => {
				pathSoFar = pathSoFar ? `${pathSoFar}>${group}` : group;

				if (!currentLevel[group]) {
					currentLevel[group] = {
						options: [],
						subGroups: {}
					};
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
					nested['Other'] = { options: [], subGroups: {} };
				}
				nested['Other'].options.push(option);
			}
		});

		return nested;
	}

	// Initialize collapsed groups recursively
	function initializeCollapsedGroups(nested: NestedGroup, prefix = ''): Set<string> {
		if (!collapsibleGroups || !defaultCollapsed) {
			return new Set();
		}

		const collapsed = new Set<string>();

		function traverse(groups: NestedGroup, currentPrefix: string) {
			Object.keys(groups).forEach((key) => {
				const fullPath = currentPrefix ? `${currentPrefix}>${key}` : key;
				collapsed.add(fullPath);

				// Recursively traverse subgroups
				if (groups[key].subGroups && Object.keys(groups[key].subGroups).length > 0) {
					traverse(groups[key].subGroups, fullPath);
				}
			});
		}

		traverse(nested, prefix);
		return collapsed;
	}

	// Get all options from a nested group recursively
	function getAllOptionsFromGroup(group: { options: Option[]; subGroups: NestedGroup }): Option[] {
		let allOptions = [...group.options];

		Object.values(group.subGroups).forEach((subGroup) => {
			allOptions = [...allOptions, ...getAllOptionsFromGroup(subGroup)];
		});

		return allOptions;
	}

	// fetch options
	async function fetchOptions() {
		isLoading = true;
		try {
			let endpoint = `/${optionsEndpoint}`;
			const collected: any[] = [];
			while (endpoint) {
				const response = await fetch(endpoint);
				if (!response.ok) break;
				const json = await response.json();
				const page = json?.results ?? json;
				collected.push(...page);
				endpoint = json?.next ?? null;
			}
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

				// Create nested structure
				nestedGroups = createNestedGroups(options);

				// Initialize collapsed state
				if (collapsibleGroups && defaultCollapsed) {
					collapsedGroups = initializeCollapsedGroups(nestedGroups);
				}
			}

			// init selection
			if ($value) {
				selected = Array.isArray($value) ? $value : [$value];
			}
		} catch (err) {
			console.error('Error fetching options', err);
		} finally {
			isLoading = false;
		}
	}

	function toggle(val: string | number) {
		if (selected.includes(val)) {
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

	function selectAllInGroup(group: { options: Option[]; subGroups: NestedGroup }) {
		const allOptions = getAllOptionsFromGroup(group);
		const groupValues = allOptions.map((opt) => opt.value);

		// Check if all options in group are already selected
		const allSelected = groupValues.every((val) => selected.includes(val));

		if (allSelected) {
			// Deselect all in group
			selected = selected.filter((val) => !groupValues.includes(val));
		} else {
			// Select all in group
			const newSelected = [...selected];
			groupValues.forEach((val) => {
				if (!newSelected.includes(val)) {
					newSelected.push(val);
				}
			});
			selected = newSelected;
		}

		$value = selected;
		cacheLock.resolve(selected);
		cachedValue = selected;
	}

	function getGroupSelectionState(group: { options: Option[]; subGroups: NestedGroup }) {
		const allOptions = getAllOptionsFromGroup(group);
		const groupValues = allOptions.map((opt) => opt.value);
		const selectedInGroup = groupValues.filter((val) => selected.includes(val));

		if (selectedInGroup.length === 0) return 'none';
		if (selectedInGroup.length === groupValues.length) return 'all';
		return 'partial';
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
		{@const totalOptions = getAllOptionsFromGroup(group).length}

		<div class="border border-gray-200 rounded-lg" style="margin-left: {depth * 20}px;">
			{#if showGroupHeaders && groupBy}
				<div
					class="px-3 py-2 border-b border-gray-200 flex items-center justify-between"
					class:bg-gray-50={depth === 0}
					class:bg-gray-100={depth === 1}
					class:bg-gray-200={depth >= 2}
				>
					<div class="flex items-center gap-2">
						{#if collapsibleGroups}
							<button
								type="button"
								aria-label="Toggle Group"
								class="text-gray-500 hover:text-gray-700 transition-transform duration-200"
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
						<h3 class="text-sm font-medium text-gray-700" class:font-bold={depth === 0}>
							{safeTranslate(groupName)}
						</h3>
						<span class="text-xs text-gray-500">({totalOptions})</span>
					</div>

					<button
						type="button"
						class="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 transition-colors"
						class:bg-blue-50={getGroupSelectionState(group) === 'all'}
						class:border-blue-300={getGroupSelectionState(group) === 'all'}
						class:bg-blue-25={getGroupSelectionState(group) === 'partial'}
						class:border-blue-200={getGroupSelectionState(group) === 'partial'}
						onclick={() => selectAllInGroup(group)}
						{disabled}
					>
						{#if getGroupSelectionState(group) === 'all'}
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
							<label class="flex items-center gap-2 hover:bg-gray-50 p-1 rounded transition-colors">
								<input
									type="checkbox"
									value={opt.value}
									checked={selected.includes(opt.value)}
									onchange={() => toggle(opt.value)}
									{disabled}
									class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
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
		<label class="text-sm font-semibold">{label}{mandatory ? ' *' : ''}</label>
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
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}

	{#each selected as val}
		<input type="hidden" name={field} value={val} />
	{/each}
</div>

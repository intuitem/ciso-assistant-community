<script lang="ts">
	import { onMount, getContext, onDestroy } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock } from '$lib/utils/types';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';

	interface Option {
		label: string;
		value: string | number;
		group?: string;
		groupsList?: string[];
		translatedLabel?: string;
	}

	interface GroupedOptions {
		[groupName: string]: Option[];
	}

	interface Props {
		form: SuperForm<Record<string, unknown>, any>;
		field: string;
		label?: string;
		helpText?: string;
		optionsEndpoint: string;
		optionsLabelField?: string;
		groupBy?: { field: string; path: string[] }[] | string; // Support multiple grouping fields for sub-grouping and path for nested fields
		cacheLock?: CacheLock;
		cachedValue?: (string | number)[] | undefined;
		translateOptions?: boolean;
		disabled?: boolean;
		mandatory?: boolean;
		showGroupHeaders?: boolean; // Control group header visibility
		collapsibleGroups?: boolean; // Make groups collapsible
		defaultCollapsed?: boolean; // Control default collapse state
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
	let groupedOptions: GroupedOptions = $state({});
	let collapsedGroups: Set<string> = $state(new Set());
	let selected: (string | number)[] = $state([]);
	let isLoading = $state(false);

	// Helper function to create group key from groupsList
	function createGroupKey(groupsList: string[]): string {
		return groupsList.filter(Boolean).join(' > ') || 'Other';
	}

	// Helper function to initialize collapsed groups
	function initializeCollapsedGroups(grouped: GroupedOptions): Set<string> {
		if (!collapsibleGroups || !defaultCollapsed) {
			return new Set();
		}
		return new Set(Object.keys(grouped));
	}

	// Group options by their group fields
	function groupOptions(opts: Option[]): GroupedOptions {
		if (!groupBy) {
			return { All: opts };
		}

		const grouped: GroupedOptions = {};

		opts.forEach((option) => {
			const groupKey = createGroupKey(option.groupsList || []);

			if (!grouped[groupKey]) {
				grouped[groupKey] = [];
			}
			grouped[groupKey].push(option);
		});

		return grouped;
	}

	// fetch options
	async function fetchOptions() {
		isLoading = true;
		try {
			let endpoint = `/${optionsEndpoint}`;
			const response = await fetch(endpoint);
			if (response.ok) {
				const data = await response.json().then((res) => res?.results ?? res);

				options = data.map((option: any) => {
					const label = option[optionsLabelField] ?? '--';
					const groupsList = Array.isArray(groupBy)
						? groupBy
								.map((group) => {
									let grp = option[group.field];
									for (const p of group.path) {
										grp = grp?.[p];
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

				// Group the options
				groupedOptions = groupOptions(options);

				// Initialize collapsed state after grouping
				if (collapsibleGroups && defaultCollapsed) {
					collapsedGroups = initializeCollapsedGroups(groupedOptions);
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
	}

	function toggleGroup(groupName: string) {
		if (!collapsibleGroups) return;

		if (collapsedGroups.has(groupName)) {
			collapsedGroups.delete(groupName);
		} else {
			collapsedGroups.add(groupName);
		}
		collapsedGroups = new Set(collapsedGroups);
	}

	function selectAllInGroup(groupName: string) {
		const groupOptions = groupedOptions[groupName] || [];
		const groupValues = groupOptions.map((opt) => opt.value);

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
	}

	function getGroupSelectionState(groupName: string) {
		const groupOptions = groupedOptions[groupName] || [];
		const groupValues = groupOptions.map((opt) => opt.value);
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
		}
	});

	onDestroy(() => {
		cacheLock.resolve(selected);
	});
</script>

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
			{#each Object.entries(groupedOptions) as [groupName, groupOpts]}
				<div class="border border-gray-200 rounded-lg">
					{#if showGroupHeaders && groupBy}
						<div
							class="bg-gray-50 px-3 py-2 border-b border-gray-200 flex items-center justify-between"
						>
							<div class="flex items-center gap-2">
								{#if collapsibleGroups}
									<button
										type="button"
										aria-label="Toggle Group"
										class="text-gray-500 hover:text-gray-700 transition-transform duration-200"
										class:rotate-90={!collapsedGroups.has(groupName)}
										onclick={() => toggleGroup(groupName)}
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
								<h3 class="text-sm font-medium text-gray-700">{safeTranslate(groupName)}</h3>
								<span class="text-xs text-gray-500">({groupOpts.length})</span>
							</div>

							<button
								type="button"
								class="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 transition-colors"
								class:bg-blue-50={getGroupSelectionState(groupName) === 'all'}
								class:border-blue-300={getGroupSelectionState(groupName) === 'all'}
								class:bg-blue-25={getGroupSelectionState(groupName) === 'partial'}
								class:border-blue-200={getGroupSelectionState(groupName) === 'partial'}
								onclick={() => selectAllInGroup(groupName)}
								{disabled}
							>
								{#if getGroupSelectionState(groupName) === 'all'}
									Deselect All
								{:else}
									Select All
								{/if}
							</button>
						</div>
					{/if}

					{#if !collapsibleGroups || !collapsedGroups.has(groupName)}
						<div class="p-3 space-y-2">
							{#each groupOpts as opt}
								<label
									class="flex items-center gap-2 hover:bg-gray-50 p-1 rounded transition-colors"
								>
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
				</div>
			{/each}
		</div>
	{/if}

	{#if helpText}
		<p class="text-sm text-gray-500">{helpText}</p>
	{/if}

	{#each selected as val}
		<input type="hidden" name={field} value={val} />
	{/each}
</div>

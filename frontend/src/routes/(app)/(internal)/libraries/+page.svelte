<script lang="ts">
	import { m } from '$paraglide/messages';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import UploadLibraryModal from '$lib/components/Modals/UploadLibraryModal.svelte';
	import {
		getModalStore,
		type ModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	import { safeTranslate } from '$lib/utils/i18n';

	let { data } = $props();

	const modalStore: ModalStore = getModalStore();

	function modalCreateForm(): void {
		let modalComponent: ModalComponent = {
			ref: UploadLibraryModal
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('addYourLibrary')
		};
		modalStore.trigger(modal);
	}

	interface QuickFilters {
		object_type: Set<string>;
		is_update: boolean;
	}
	let quickFilterValues: QuickFilters = {
		object_type: new Set(),
		is_update: false
	};

	type FilterConfig = {
		icon: string;
		selectedClass: string;
		hoverClass: string;
		label: string;
	};

	const filterConfiguration: Record<string, FilterConfig> = {
		frameworks: {
			icon: 'fa-book-open',
			selectedClass: 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-blue-200',
			hoverClass: 'hover:border-blue-400 hover:bg-blue-50',
			label: m.frameworks()
		},
		reference_controls: {
			icon: 'fa-shield-halved',
			selectedClass:
				'bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-emerald-200',
			hoverClass: 'hover:border-emerald-400 hover:bg-emerald-50',
			label: m.referenceControls()
		},
		risk_matrices: {
			icon: 'fa-table-cells',
			selectedClass: 'bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-amber-200',
			hoverClass: 'hover:border-amber-400 hover:bg-amber-50',
			label: m.riskMatrices()
		},
		threats: {
			icon: 'fa-triangle-exclamation',
			selectedClass: 'bg-gradient-to-r from-red-400 to-red-500 text-white shadow-red-200',
			hoverClass: 'hover:border-red-400 hover:bg-red-50',
			label: m.threats()
		},
		metric_definitions: {
			icon: 'fa-chart-line',
			selectedClass: 'bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-purple-200',
			hoverClass: 'hover:border-purple-400 hover:bg-purple-50',
			label: m.metricDefinitions()
		},
		requirement_mapping_sets: {
			icon: 'fa-diagram-project',
			selectedClass: 'bg-gradient-to-r from-pink-500 to-pink-600 text-white shadow-pink-200',
			hoverClass: 'hover:border-pink-400 hover:bg-pink-50',
			label: m.requirementMappingSets()
		}
	};

	const updatableFilterConfig: FilterConfig = {
		icon: 'fa-rotate',
		selectedClass: 'bg-gradient-to-r from-teal-500 to-teal-600 text-white shadow-teal-200',
		hoverClass: 'hover:border-teal-400 hover:bg-teal-50',
		label: m.updateAvailable()
	};

	const filterTypes = Object.keys(filterConfiguration);

	let quickFilterSelected: Record<string, boolean> = $state({});
	let updatableFilterSelected: boolean = $state(false);
</script>

<div class="card bg-white py-2 shadow-sm">
	<ModelTable
		source={data.storedLibrariesTable}
		URLModel="stored-libraries"
		deleteForm={data.deleteForm}
		onFilterChange={(filters) => {
			const objectTypeValues = filters['object_type'] ?? [];
			const filteredObjectTypes = objectTypeValues.map((filter) => filter.value);
			const filterKeys = Object.keys(quickFilterSelected);

			filterKeys.forEach((filterKey) => {
				quickFilterSelected[filterKey] = filteredObjectTypes.includes(filterKey);
			});
			filteredObjectTypes.forEach((filterKey) => {
				quickFilterSelected[filterKey] = true;
			});

			// Handle is_update filter state
			const isUpdateValue = filters['is_update'];
			updatableFilterSelected = isUpdateValue === 'true' || isUpdateValue === true;
			quickFilterValues.is_update = updatableFilterSelected;
		}}
	>
		{#snippet quickFilters(filterValues, form, invalidateTable)}
			<div
				class="flex flex-wrap gap-2 p-3 bg-gradient-to-r from-gray-50 to-white rounded-lg border border-gray-200"
			>
				{#each filterTypes as objectType}
					{@const config = filterConfiguration[objectType]}

					<button
						class="group relative px-4 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ease-out transform hover:scale-105 active:scale-95 shadow-sm hover:shadow-md
                        {quickFilterSelected[objectType]
							? config.selectedClass
							: `bg-white text-gray-700 border-2 border-gray-300 ${config.hoverClass}`}"
						onclick={() => {
							const filterValue = filterValues['object_type'];
							const filteredTypes = filterValue.map((obj) => obj.value);

							const removeFilter = quickFilterValues.object_type.has(objectType);
							if (removeFilter) {
								quickFilterValues.object_type.delete(objectType);
								filterValues['object_type'] = filterValue.filter((obj) => obj.value !== objectType);
							} else {
								quickFilterValues.object_type.add(objectType);
								const isSelected = filteredTypes.includes(objectType);
								if (!isSelected) {
									filterValues['object_type'] = [...filterValue, { value: objectType }];
								}
							}

							const newFilteredTypes = filterValues['object_type'].map((obj) => obj.value);
							form.form.update((currentData) => {
								currentData['object_type'] = newFilteredTypes.length > 0 ? newFilteredTypes : null;
								return currentData;
							});

							invalidateTable();
						}}
					>
						<span class="flex items-center gap-2">
							<i
								class="fa-solid {config.icon} transition-transform duration-200 {quickFilterSelected[
									objectType
								]
									? 'scale-110'
									: 'group-hover:scale-110'}"
							></i>
							<span class="font-semibold">{config.label}</span>
							{#if quickFilterSelected[objectType]}
								<svg class="h-4 w-4 ml-1" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</span>
					</button>
				{/each}
				<button
					class="group relative px-4 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ease-out transform hover:scale-105 active:scale-95 shadow-sm hover:shadow-md
                    {updatableFilterSelected
						? updatableFilterConfig.selectedClass
						: `bg-white text-gray-700 border-2 border-gray-300 ${updatableFilterConfig.hoverClass}`}"
					onclick={() => {
						quickFilterValues.is_update = !quickFilterValues.is_update;
						updatableFilterSelected = quickFilterValues.is_update;

						form.form.update((currentData) => {
							currentData['is_update'] = quickFilterValues.is_update ? 'true' : null;
							return currentData;
						});

						invalidateTable();
					}}
				>
					<span class="flex items-center gap-2">
						<i
							class="fa-solid {updatableFilterConfig.icon} transition-transform duration-200 {updatableFilterSelected
								? 'scale-110'
								: 'group-hover:scale-110'}"
						></i>
						<span class="font-semibold">{updatableFilterConfig.label}</span>
						{#if updatableFilterSelected}
							<svg class="h-4 w-4 ml-1" fill="currentColor" viewBox="0 0 20 20">
								<path
									fill-rule="evenodd"
									d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
									clip-rule="evenodd"
								/>
							</svg>
						{/if}
					</span>
				</button>
			</div>
		{/snippet}
		{#snippet addButton()}
			<div>
				<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
					<button
						class="inline-block p-3 btn-mini-primary w-12 focus:relative"
						data-testid="add-button"
						title={m.addYourLibrary()}
						onclick={modalCreateForm}
						><i class="fa-solid fa-file-circle-plus"></i>
					</button>
				</span>
			</div>
		{/snippet}
	</ModelTable>
</div>

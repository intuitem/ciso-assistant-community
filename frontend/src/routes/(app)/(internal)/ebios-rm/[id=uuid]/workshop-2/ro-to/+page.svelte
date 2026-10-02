<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RoToRadarChart from '$lib/components/Chart/RoToRadarChart.svelte';
	import { ratingLevelLabel } from '$lib/utils/ebios-rating-kit';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import { page } from '$app/state';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const URLModel = data.URLModel;

	function modalCreateForm(): void {
		let modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.createForm,
				model: data.model
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + data.model.localName)
		};
		modalStore.trigger(modal);
	}

	let radarOpen = $state(['']);
	const pertinenceLabels = $derived(
		(data.pertinenceLevels ?? []).map((level: any) => ratingLevelLabel(level))
	);
	const radarCouples = $derived(
		(data.couples ?? []).map((couple: any) => ({
			...couple,
			risk_origin: safeTranslate(couple.risk_origin),
			target_objective_category: couple.target_objective_category
				? safeTranslate(couple.target_objective_category.str)
				: m.roToRadarNoCategory()
		}))
	);
	const radarOrigins = $derived(
		[...new Set(radarCouples.map((couple: any) => couple.risk_origin))].sort() as string[]
	);
	// Optional M2_09 filter: hide some risk origins from both views.
	let hiddenOrigins: string[] = $state([]);
	const shownCouples = $derived(
		radarCouples.filter((couple: any) => !hiddenOrigins.includes(couple.risk_origin))
	);
	function toggleOrigin(origin: string) {
		hiddenOrigins = hiddenOrigins.includes(origin)
			? hiddenOrigins.filter((o) => o !== origin)
			: [...hiddenOrigins, origin];
	}

	let activeActivity: string | null = $state(null);
	page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		} else if (key === 'activity' && value === 'three') {
			activeActivity = 'three';
		}
	});
</script>

<div class="flex items-center justify-between mb-4">
	<Anchor
		breadcrumbAction="push"
		href={`/ebios-rm/${data.data.id}`}
		class="flex items-center space-x-2 text-primary-800-200 hover:text-primary-600-400"
	>
		<i class="fa-solid fa-arrow-left"></i>
		<p>{m.goBackToEbiosRmStudy()}</p>
	</Anchor>
</div>
<div class="space-y-2">
	<Accordion
		class="bg-surface-50-950 rounded-md border hover:text-primary-700 text-surface-950-50"
		value={radarOpen}
		onValueChange={(e) => (radarOpen = e.value)}
		collapsible
	>
		<Accordion.Item value="radar">
			<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
				<i class="fa-solid fa-bullseye mr-2"></i><span class="flex-1 text-left"
					>{m.roToRadar()}</span
				>
				<Accordion.ItemIndicator
					class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
					><i class="fa-solid fa-chevron-down text-xs"></i></Accordion.ItemIndicator
				>
			</Accordion.ItemTrigger>
			<Accordion.ItemContent>
				{#if radarOpen.includes('radar')}
					{#if radarCouples.length}
						<div class="space-y-2 p-2">
							<div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-surface-600-400">
								<span class="flex items-center gap-1"
									><span class="inline-block size-3 rounded-full" style="background:#e53935"
									></span>{m.selected()}</span
								>
								<span class="flex items-center gap-1"
									><span class="inline-block size-3 rounded-full" style="background:#43a047"
									></span>{m.notSelected()}</span
								>
								<span>{m.roToRadarHelp()}</span>
							</div>
							<div class="flex flex-wrap gap-2" data-testid="ro-to-radar-filter">
								{#each radarOrigins as origin}
									<button
										type="button"
										class="badge text-xs {hiddenOrigins.includes(origin)
											? 'preset-tonal-surface line-through opacity-60'
											: 'preset-tonal-primary'}"
										aria-pressed={!hiddenOrigins.includes(origin)}
										onclick={() => toggleOrigin(origin)}>{origin}</button
									>
								{/each}
							</div>
							{#key shownCouples}
								<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
									<RoToRadarChart
										couples={shownCouples}
										{pertinenceLabels}
										groupBy="origin"
										name="ro_to_by_origin"
										title={m.roToRadarByOrigin()}
									/>
									<RoToRadarChart
										couples={shownCouples}
										{pertinenceLabels}
										groupBy="objective"
										name="ro_to_by_objective"
										title={m.roToRadarByObjective()}
									/>
								</div>
							{/key}
						</div>
					{:else}
						<p class="text-sm text-surface-600-400">{m.noRoToCouples()}</p>
					{/if}
				{/if}
			</Accordion.ItemContent>
		</Accordion.Item>
	</Accordion>
	<ModelTable
		source={data.table}
		deleteForm={data.deleteForm}
		{URLModel}
		detailQueryParameter={`activity=${activeActivity}`}
		baseEndpoint="/ro-to?ebios_rm_study={page.params.id}"
	>
		{#snippet addButton()}
			<div>
				<span class="inline-flex overflow-hidden rounded-md border bg-surface-50-950 shadow-xs">
					<button
						class="inline-block p-3 btn-mini-primary w-12 focus:relative"
						data-testid="add-button"
						title={safeTranslate('add-' + data.model.localName)}
						onclick={modalCreateForm}
						><i class="fa-solid fa-file-circle-plus"></i>
					</button>
				</span>
			</div>
		{/snippet}
	</ModelTable>
</div>

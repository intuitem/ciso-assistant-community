<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import EcosystemCircularRadarChart from '$lib/components/Chart/EcosystemCircularRadarChart.svelte';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

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
	let value = $state(['']);
</script>

<div class="flex items-center justify-between mb-4">
	<Anchor
		breadcrumbAction="push"
		href={`/ebios-rm/${data.data.id}`}
		class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
	>
		<i class="fa-solid fa-arrow-left"></i>
		<p>{m.goBackToEbiosRmStudy()}</p>
	</Anchor>
</div>

<div class="space-y-2">
	<Accordion
		class="bg-white rounded-md border hover:text-primary-700 text-gray-800"
		{value}
		onValueChange={(e) => (value = e.value)}
		hover="bg-white"
		collapsible
	>
		<Accordion.Item value="summary">
			{#snippet control()}
				<i class="fa-solid fa-bullseye"></i>
				{m.ecosystemRadar()}
			{/snippet}
			{#snippet panel()}
				<div class="bg-white flex flex-col space-y-4">
					<div class="flex w-full h-fit">
						<EcosystemCircularRadarChart
							title={m.current()}
							name="c_ecosystem_circular"
							data={data.circularRadar}
							type="current"
							classesContainer="w-full"
							height="h-screen"
						/>
						<EcosystemCircularRadarChart
							title={m.residual()}
							name="r_ecosystem_circular"
							data={data.circularRadar}
							type="residual"
							classesContainer="w-full"
							height="h-screen"
						/>
					</div>
				</div>
			{/snippet}
		</Accordion.Item>
	</Accordion>
	<ModelTable
		source={data.table}
		deleteForm={data.deleteForm}
		{URLModel}
		baseEndpoint="/stakeholders?ebios_rm_study={page.params.id}"
	>
		{#snippet addButton()}
			<div>
				<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
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

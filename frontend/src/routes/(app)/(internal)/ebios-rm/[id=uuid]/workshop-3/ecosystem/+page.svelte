<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import EcosystemRadarChart from '$lib/components/Chart/EcosystemRadarChart.svelte';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import { page } from '$app/stores';

	const modalStore: ModalStore = getModalStore();

	export let data: PageData;

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
</script>

<div class="space-y-2">
	<Accordion
		class="bg-white rounded-md border hover:text-primary-700 text-gray-800"
		hover="bg-white"
	>
		<AccordionItem>
			<svelte:fragment slot="lead"><i class="fa-solid fa-bullseye"></i></svelte:fragment>
			<svelte:fragment slot="summary">{m.ecosystemRadar()}</svelte:fragment>
			<svelte:fragment slot="content">
				<div class="bg-white flex">
					<div class="flex w-full h-fit">
						<EcosystemRadarChart
							title={m.current()}
							name="c_ecosystem"
							data={data.radar.current}
							classesContainer="w-full"
							height="h-screen"
						/>
						<EcosystemRadarChart
							title={m.residual()}
							name="r_ecosystem"
							classesContainer="w-full"
							height="h-screen"
							data={data.radar.residual}
						/>
					</div>
				</div>
			</svelte:fragment>
		</AccordionItem>
	</Accordion>
	<ModelTable
		source={data.table}
		deleteForm={data.deleteForm}
		{URLModel}
		baseEndpoint="/stakeholders?ebios_rm_study={$page.params.id}"
	>
		<div slot="addButton">
			<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm">
				<button
					class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
					data-testid="add-button"
					title={safeTranslate('add-' + data.model.localName)}
					on:click={modalCreateForm}
					><i class="fa-solid fa-file-circle-plus"></i>
				</button>
			</span>
		</div>
	</ModelTable>
</div>

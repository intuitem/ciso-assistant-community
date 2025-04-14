<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';

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
	const missingScenarios = data.scenariosWithoutAttackPath;
</script>

{#if missingScenarios.length > 0}
	<section class="my-6">
		<div
			class="flex items-start gap-3 rounded-xl border border-yellow-300 bg-yellow-100 p-4 shadow-sm"
		>
			<div class="text-yellow-600 mt-1">
				<i class="fa-solid fa-triangle-exclamation text-xl"></i>
			</div>
			<div>
				<h2 class="font-semibold text-yellow-800 text-md mb-1">
					{m.reminderWarningStrategicScenarios()}
				</h2>
				<p class="text-yellow-700 text-sm leading-snug mb-1">
					{m.addAttackPathToDoOperationalScenarios()}
				</p>
				<ul class="list-disc list-inside text-yellow-700 text-sm">
					{#each missingScenarios as scenario}
						<li>{scenario.name ?? `ID: ${scenario.id}`}</li>
					{/each}
				</ul>
			</div>
		</div>
	</section>
{/if}
<ModelTable
	source={data.table}
	deleteForm={data.deleteForm}
	{URLModel}
	baseEndpoint="/strategic-scenarios?ebios_rm_study={$page.params.id}"
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

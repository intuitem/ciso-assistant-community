<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
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

{#if data.scenariosWithoutAttackPath.count > 0}
	{@const missingScenarios = data.scenariosWithoutAttackPath.results}
	<section class="my-6">
		<div
			class="flex items-start gap-3 rounded-xl border border-warning-300 bg-warning-100 p-4 shadow-xs"
		>
			<div class="text-warning-600 mt-1">
				<i class="fa-solid fa-triangle-exclamation text-xl"></i>
			</div>
			<div>
				<h2 class="font-semibold text-warning-800 text-md mb-1">
					{m.reminderWarningStrategicScenarios()}
				</h2>
				<p class="text-warning-700 text-sm leading-snug mb-1">
					{m.addAttackPathToDoOperationalScenarios()}
				</p>
				<ul class="list-disc list-inside text-warning-700 text-sm">
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
	baseEndpoint="/strategic-scenarios?ebios_rm_study={page.params.id}"
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

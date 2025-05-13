<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { page } from '$app/stores';

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

<ModelTable
	source={data.table}
	deleteForm={data.deleteForm}
	{URLModel}
	baseEndpoint="/risk-assessments/?ebios_rm_study={$page.params.id}"
>
	{#snippet addButton()}
		<div >
			<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm">
				<button
					class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
					data-testid="add-button"
					title={safeTranslate('add-' + data.model.localName)}
					onclick={modalCreateForm}
					><i class="fa-solid fa-file-circle-plus"></i>
				</button>
			</span>
		</div>
	{/snippet}
</ModelTable>

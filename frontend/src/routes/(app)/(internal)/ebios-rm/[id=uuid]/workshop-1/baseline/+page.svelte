<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import UpdateModal from '$lib/components/Modals/UpdateModal.svelte';

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

	function modalUpdateForm(): void {
		let modalComponent: ModalComponent = {
			ref: UpdateModal,
			props: {
				form: data.updateForm,
				model: data.updatedModel,
				object: data.object,
				context: 'selectAudit'
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.selectAudit()
		};
		modalStore.trigger(modal);
	}
</script>

<ModelTable
	source={data.table}
	deleteForm={data.deleteForm}
	{URLModel}
	baseEndpoint="/compliance-assessments?ebios_rm_studies={data.data.id}"
>
	<div slot="optButton">
		<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm">
			<button
				class="inline-block border-e p-3 btn-mini-secondary w-12 focus:relative"
				data-testid="opt-button"
				title={m.selectAudit()}
				on:click={modalUpdateForm}
				><i class="fa-solid fa-hand-pointer"></i>
			</button>
		</span>
	</div>
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

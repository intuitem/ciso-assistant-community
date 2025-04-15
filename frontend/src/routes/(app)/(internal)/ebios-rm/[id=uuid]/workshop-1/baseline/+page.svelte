<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import UpdateModal from '$lib/components/Modals/UpdateModal.svelte';
	import { canPerformAction } from '$lib/utils/access-control';
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

	const user = $page.data.user;
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: data.model.name,
		domain:
			data.model.name === 'folder'
				? data.data.id
				: (data.data.folder?.id ?? data.data.folder ?? user.root_folder_id)
	});
</script>

<ModelTable
	source={data.table}
	deleteForm={data.deleteForm}
	{URLModel}
	canSelectObject={canEditObject}
	baseEndpoint="/compliance-assessments?ebios_rm_studies={data.data.id}"
>
	<div slot="selectButton">
		<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm">
			<button
				class="inline-block border-e p-3 btn-mini-secondary w-12 focus:relative"
				data-testid="select-button"
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

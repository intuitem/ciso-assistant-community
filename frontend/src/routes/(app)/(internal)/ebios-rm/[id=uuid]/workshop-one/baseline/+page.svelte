<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import MissingConstraintsModal from '$lib/components/Modals/MissingConstraintsModal.svelte';
	import { checkConstraints } from '$lib/utils/crud';
	import * as m from '$paraglide/messages.js';
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
		if (
			checkConstraints(
				data.createForm.constraints,
				Object.fromEntries(
					Object.entries(data.model.foreignKeys).filter(([key]) => key !== 'risk_matrix')
				)
			).length > 0
		) {
			modalComponent = {
				ref: MissingConstraintsModal
			};
			modal = {
				type: 'component',
				component: modalComponent,
				title: m.warning(),
				body: safeTranslate('add-' + data.model.localName).toLowerCase(),
				value: checkConstraints(data.createForm.constraints, data.model.foreignKeys)
			};
		}
		modalStore.trigger(modal);
	}

	function modalUpdateForm(): void {
		let modalComponent: ModalComponent = {
			ref: UpdateModal,
			props: {
				form: data.updateForm,
				model: data.updatedModel,
				object: data.object,
				foreignKeys: data.updatedModel.foreignKeys,
				context: 'selectAudit'
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.selectAudit()
		};
		if (
			checkConstraints(
				data.updateForm.constraints,
				Object.fromEntries(
					Object.entries(data.updatedModel.foreignKeys).filter(([key]) => key !== 'risk_matrix')
				)
			).length > 0
		) {
			modalComponent = {
				ref: MissingConstraintsModal
			};
			modal = {
				type: 'component',
				component: modalComponent,
				title: m.warning(),
				body: safeTranslate('add-' + data.updatedModel.localName).toLowerCase(),
				value: checkConstraints(data.updateForm.constraints, data.updatedModel.foreignKeys)
			};
		}
		modalStore.trigger(modal);
	}
</script>

<ModelTable source={data.table} deleteForm={data.deleteForm} {URLModel}>
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

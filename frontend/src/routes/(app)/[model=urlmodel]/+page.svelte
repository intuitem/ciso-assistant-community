<script lang="ts">
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import MissingConstraintsModal from '$lib/components/Modals/MissingConstraintsModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	import { capitalizeFirstLetter } from '$lib/utils/locales';
	import { checkConstraints } from '$lib/utils/crud';

	export let data: PageData;

	const modalStore: ModalStore = getModalStore();

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
			title: m['add' + capitalizeFirstLetter(data.model.localName)]()
		};
		if (checkConstraints(data.createForm.constraints, data.model.foreignKeys).length > 0) {
			modalComponent = {
				ref: MissingConstraintsModal
			};
			modal = {
				type: 'component',
				component: modalComponent,
				title: m.warning(),
				body: m['add' + capitalizeFirstLetter(data.model.localName)]().toLowerCase(),
				value: checkConstraints(data.createForm.constraints, data.model.foreignKeys)
			};
		}
		modalStore.trigger(modal);
	}
</script>

{#if data.table}
	<div class="shadow-lg">
		<ModelTable source={data.table} deleteForm={data.deleteForm} URLModel={data.URLModel}>
			<div slot="addButton">
				{#if !['risk-matrices', 'frameworks', 'user-groups', 'role-assignments'].includes(data.URLModel)}
					<button
						class="btn variant-filled-primary self-end"
						data-testid="add-button"
						on:click={modalCreateForm}
						><i class="fa-solid fa-plus mr-2" />
						{m['add' + capitalizeFirstLetter(data.model.localName)]()}
					</button>
				{:else if data.URLModel === 'risk-matrices'}
					<a href="/libraries" class="btn variant-filled-primary" data-testid="add-button"
						><i class="fa-solid fa-file-import mr-2" />{m.importMatrices()}</a
					>
				{:else if data.URLModel === 'frameworks'}
					<a href="/libraries" class="btn variant-filled-primary" data-testid="add-button"
						><i class="fa-solid fa-file-import mr-2" />{m.importFrameworks()}</a
					>
				{/if}
			</div>
		</ModelTable>
	</div>
{/if}

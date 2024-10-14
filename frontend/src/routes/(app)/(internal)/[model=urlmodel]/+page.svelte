<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
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
	$: URLModel = data.URLModel;

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
			title: safeTranslate('add' + capitalizeFirstLetter(data.model.localName))
		};
		if (checkConstraints(data.createForm.constraints, data.model.foreignKeys).length > 0) {
			modalComponent = {
				ref: MissingConstraintsModal
			};
			modal = {
				type: 'component',
				component: modalComponent,
				title: m.warning(),
				body: safeTranslate('add' + capitalizeFirstLetter(data.model.localName)).toLowerCase(),
				value: checkConstraints(data.createForm.constraints, data.model.foreignKeys)
			};
		}
		modalStore.trigger(modal);
	}
</script>

{#if data.table}
	<div class="shadow-lg">
		{#key URLModel}
			{@debug URLModel}
			<ModelTable source={data.table} deleteForm={data.deleteForm} {URLModel}>
				<div slot="addButton">
					{#if !['risk-matrices', 'frameworks', 'requirement-mapping-sets', 'user-groups', 'role-assignments'].includes(URLModel)}
						<button
							class="btn variant-filled-primary self-end"
							data-testid="add-button"
							on:click={modalCreateForm}
							><i class="fa-solid fa-plus mr-2" />
							{safeTranslate('add' + capitalizeFirstLetter(data.model.localName))}
						</button>
						{#if URLModel === 'applied-controls'}
							<a
								href="{URLModel}/export/"
								class="btn variant-filled-surface"
								data-testid="export-button"
								><i class="fa-solid fa-download mr-2" />{m.exportButton()}</a
							>
						{/if}
					{:else if URLModel === 'risk-matrices'}
						<a href="/libraries" class="btn variant-filled-primary" data-testid="add-button"
							><i class="fa-solid fa-file-import mr-2" />{m.importMatrices()}</a
						>
					{:else if URLModel === 'frameworks'}
						<a href="/libraries" class="btn variant-filled-primary" data-testid="add-button"
							><i class="fa-solid fa-file-import mr-2" />{m.importFrameworks()}</a
						>
					{:else if URLModel === 'requirement-mapping-sets'}
						<a href="/libraries" class="btn variant-filled-primary" data-testid="add-button"
							><i class="fa-solid fa-file-import mr-2" />{m.importMappings()}</a
						>
					{/if}
				</div>
			</ModelTable>
		{/key}
	</div>
{/if}

<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { consumeCreateIntent } from '$lib/utils/create-intent';

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

	$effect(() => {
		consumeCreateIntent({ urlModel: URLModel, modelName: data.model.name, open: modalCreateForm });
	});
</script>

<ModelTable source={data.table} deleteForm={data.deleteForm} {URLModel}>
	{#snippet addButton()}
		<div>
			<span class="inline-flex overflow-hidden rounded-md border bg-surface-50-950 shadow-xs">
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

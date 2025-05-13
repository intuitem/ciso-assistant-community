<script lang="ts">
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { PageData, ActionData } from './$types';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	let URLModel = $derived(data.URLModel);

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
			title: safeTranslate('add-' + data.model.localName)
		};
		modalStore.trigger(modal);
	}
</script>

{#if data.table}
	<div class="shadow-lg">
		{#key URLModel}
			<ModelTable source={data.table} deleteForm={data.deleteForm} {URLModel}>
				{#snippet addButton()}
								<div >
						<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm">
							{#if !['risk-matrices', 'frameworks', 'requirement-mapping-sets', 'user-groups', 'role-assignments'].includes(URLModel)}
								<button
									class="inline-block border-e p-3 text-gray-50 bg-pink-500 hover:bg-pink-400 w-12 focus:relative"
									data-testid="add-button"
									id="add-button"
									title={safeTranslate('add-' + data.model.localName)}
									onclick={modalCreateForm}
									><i class="fa-solid fa-file-circle-plus"></i>
								</button>
								{#if ['applied-controls', 'assets'].includes(URLModel)}
									<a
										href="{URLModel}/export/"
										class="inline-block p-3 text-gray-50 bg-pink-500 hover:bg-pink-400 w-12 focus:relative"
										title={m.exportButton()}
										data-testid="export-button"><i class="fa-solid fa-download mr-2"></i></a
									>
								{/if}
							{:else if URLModel === 'risk-matrices'}
								<a
									href="/libraries?object_type=risk_matrix"
									class="inline-block p-3 text-gray-50 bg-pink-500 hover:bg-pink-400 w-12 focus:relative"
									data-testid="add-button"
									id="add-button"
									title={m.importMatrices()}><i class="fa-solid fa-file-import mr-2"></i></a
								>
							{:else if URLModel === 'frameworks'}
								<a
									href="/libraries?object_type=framework"
									class="inline-block p-3 text-gray-50 bg-pink-500 hover:bg-pink-400 w-12 focus:relative"
									data-testid="add-button"
									id="add-button"
									title={m.importFrameworks()}><i class="fa-solid fa-file-import mr-2"></i></a
								>
							{:else if URLModel === 'requirement-mapping-sets'}
								<a
									href="/libraries?object_type=requirement_mapping_set"
									class="inline-block p-3 text-gray-50 bg-pink-500 hover:bg-pink-400 w-12 focus:relative"
									data-testid="add-button"
									id="add-button"
									title={m.importMappings()}><i class="fa-solid fa-file-import mr-2"></i></a
								>
							{/if}
						</span>
					</div>
							{/snippet}
			</ModelTable>
		{/key}
	</div>
{/if}

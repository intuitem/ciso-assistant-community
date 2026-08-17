<script lang="ts">
	import { page } from '$app/state';

	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ActionData, PageData } from './$types';
	import { m } from '$paraglide/messages';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	let URLModel = $derived(data.URLModel);

	const modalStore: ModalStore = getModalStore();
	const isAdmin = Boolean(page.data.user?.is_admin);

	function modalCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.createForm,
				model: data.model
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + data.model.localName)
		};
		modalStore.trigger(modal);
	}

	// Identity providers are gated behind IsGlobalAdmin, not the folder-scoped
	// RBAC permission catalog, so ModelTable's generic canPerformAction check
	// never sees change_socialapp/delete_socialapp and hides the built-in row
	// actions. Render our own, gated on isAdmin instead.
	function modalConfirmDelete(row: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: data.deleteForm,
				id: row.id,
				debug: false,
				URLModel
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteModalTitle(),
			body: m.deleteModalMessage({ name: row.name })
		};
		modalStore.trigger(modal);
	}
</script>

{#if data?.table}
	{#if isAdmin}
		<div class="flex justify-end mb-2">
			<div class="inline-flex overflow-hidden rounded-md border bg-surface-50-950 shadow-xs">
				<button
					class="inline-block p-3 btn-mini-primary w-12 focus:relative"
					data-testid="add-button"
					id="add-button"
					title={safeTranslate('add-' + data.model.localName)}
					aria-label={safeTranslate('add-' + data.model.localName)}
					onclick={modalCreateForm}
					><i class="fa-solid fa-file-circle-plus"></i>
				</button>
			</div>
		</div>
	{/if}
	<div class="shadow-lg">
		{#key URLModel}
			<ModelTable source={data.table} deleteForm={data.deleteForm} {URLModel}>
				{#snippet actions({ meta })}
					{#if isAdmin}
						<span
							class="space-x-2 whitespace-nowrap flex flex-row items-center text-xl text-surface-700-300 justify-end"
						>
							<Anchor
								breadcrumbAction="push"
								aria-label={m.view()}
								href={`/${URLModel}/${meta.id}`}
								class="unstyled cursor-pointer hover:text-primary-500"
								data-testid="tablerow-detail-button"><i class="fa-solid fa-eye"></i></Anchor
							>
							<Anchor
								breadcrumbAction="push"
								label={m.edit()}
								href={`/${URLModel}/${meta.id}/edit?next=${encodeURIComponent(page.url.pathname + page.url.search)}`}
								stopPropagation
								class="unstyled cursor-pointer hover:text-primary-500"
								data-testid="tablerow-edit-button"><i class="fa-solid fa-pen-to-square"></i></Anchor
							>
							<button
								onclick={(e) => {
									modalConfirmDelete(meta);
									e.stopPropagation();
								}}
								class="cursor-pointer hover:text-primary-500"
								aria-label={m.delete()}
								data-testid="tablerow-delete-button"><i class="fa-solid fa-trash"></i></button
							>
						</span>
					{/if}
				{/snippet}
			</ModelTable>
		{/key}
	</div>
{/if}

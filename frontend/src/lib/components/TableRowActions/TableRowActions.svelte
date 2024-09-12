<script lang="ts">
	import { page } from '$app/stores';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import type { ModelMapEntry } from '$lib/utils/crud';
	import type { urlModel } from '$lib/utils/types';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';

	import * as m from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	export let row: Record<string, any>;
	export let model: ModelMapEntry | undefined = undefined;

	export let detailURL: string;
	export let editURL: string | undefined;
	export let deleteForm: SuperValidated<AnyZodObject> | undefined;
	export let URLModel: urlModel | string | undefined;
	export let identifierField = 'id';
	export let preventDelete = false;

	export let hasBody = false;

	function stopPropagation(event: Event): void {
		event.stopPropagation();
	}

	function modalConfirmDelete(id: string, row: {[key: string]: any}): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: deleteForm,
				id: id,
				debug: false,
				URLModel: URLModel
			}
		};
		const name = URLModel === "users" && row.first_name ?
			`${row.first_name} ${row.last_name} (${row.email})`
				: row.name ?? Object.values(row)[0];
		const body = URLModel === "users" ?
			m.deleteUserMessage({ name: name })
				: m.deleteModalMessage({ name: name });
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.deleteModalTitle(),
			body: body
		};
		modalStore.trigger(modal);
	}

	const user = $page.data.user;
	$: canDeleteObject = Object.hasOwn(user.permissions, `delete_${model?.name}`) && !preventDelete;
	$: canEditObject = Object.hasOwn(user.permissions, `change_${model?.name}`);

	$: displayDetail = detailURL;
	$: displayEdit =
		canEditObject && URLModel && !['frameworks', 'risk-matrices'].includes(URLModel) && editURL;
	$: displayDelete = canDeleteObject && deleteForm !== undefined;
</script>

<span
	class="space-x-2 whitespace-nowrap flex flex-row items-center text-xl text-surface-700 justify-end"
>
	<slot name="head" />
	<slot name="body" />
	{#if !hasBody}
		{#if displayDetail}
			<a
				href={detailURL}
				class="unstyled cursor-pointer hover:text-primary-500"
				data-testid="tablerow-detail-button"><i class="fa-solid fa-eye" /></a
			>
		{/if}
		{#if displayEdit}
			<a
				href={editURL}
				on:click={stopPropagation}
				class="unstyled cursor-pointer hover:text-primary-500"
				data-testid="tablerow-edit-button"><i class="fa-solid fa-pen-to-square" /></a
			>
		{/if}
		{#if displayDelete}
			<button
				on:click={(_) => {
					modalConfirmDelete(row.meta[identifierField], row);
					stopPropagation(_);
				}}
				on:keydown={(_) => modalConfirmDelete(row.meta.id, row)}
				class="cursor-pointer hover:text-primary-500"
				data-testid="tablerow-delete-button"><i class="fa-solid fa-trash" /></button
			>
		{/if}
	{/if}
	<slot name="tail" />
</span>

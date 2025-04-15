<script lang="ts">
	import { page } from '$app/stores';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import type { ModelMapEntry } from '$lib/utils/crud';
	import type { urlModel } from '$lib/utils/types';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';

	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { canPerformAction } from '$lib/utils/access-control';

	const modalStore: ModalStore = getModalStore();

	export let row: Record<string, any>;
	export let model: ModelMapEntry | undefined = undefined;

	export let detailURL: string;
	export let editURL: string | undefined;
	export let deleteForm: SuperValidated<AnyZodObject> | undefined;
	export let URLModel: urlModel | string | undefined;
	export let identifierField = 'id';
	export let preventDelete = false;
	export let baseClass =
		'space-x-2 whitespace-nowrap flex flex-row items-center text-xl text-surface-700 justify-end';

	export let hasBody = false;

	function stopPropagation(event: Event): void {
		event.stopPropagation();
	}

	function modalConfirmDelete(
		id: string,
		row: { [key: string]: string | number | boolean | null }
	): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: deleteForm,
				id: id,
				debug: false,
				URLModel: URLModel
			}
		};
		const name =
			URLModel === 'users' && row.first_name
				? `${row.first_name} ${row.last_name} (${row.email})`
				: (row.name ?? Object.values(row)[0]);
		const body =
			URLModel === 'users'
				? m.deleteUserMessage({ name: name })
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

	function promptModalConfirmDelete(
		id: string,
		row: { [key: string]: string | number | boolean | null }
	): void {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: {
				_form: deleteForm,
				id: id,
				debug: false,
				URLModel: URLModel,
				formAction: '?/delete'
			}
		};
		const name =
			URLModel === 'users' && row.first_name
				? `${row.first_name} ${row.last_name} (${row.email})`
				: (row.name ?? Object.values(row)[0]);
		const body =
			URLModel === 'users'
				? m.deleteUserMessage({ name: name })
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

	$: canDeleteObject =
		!preventDelete &&
		(model
			? $page.params.id
				? canPerformAction({
						user,
						action: 'delete',
						model: model.name,
						domain:
							model.name === 'folder'
								? row.meta.id
								: (row.meta.folder?.id ?? row.meta.folder ?? user.root_folder_id)
					})
				: Object.hasOwn(user.permissions, `delete_${model.name}`)
			: false);
	$: canEditObject = model
		? $page.params.id
			? canPerformAction({
					user,
					action: 'change',
					model: model.name,
					domain:
						model.name === 'folder'
							? row.meta.id
							: (row.meta.folder?.id ?? row.meta.folder ?? user.root_folder_id)
				})
			: Object.hasOwn(user.permissions, `change_${model.name}`)
		: false;

	$: displayDetail = detailURL;
	$: displayEdit =
		canEditObject &&
		URLModel &&
		!['frameworks', 'risk-matrices', 'ebios-rm'].includes(URLModel) &&
		editURL;
	$: displayDelete = canDeleteObject && deleteForm !== undefined;
</script>

<span class={baseClass}>
	<slot name="head" />
	<slot name="body" />
	{#if !hasBody}
		{#if displayDetail}
			<Anchor
				breadcrumbAction="push"
				href={detailURL}
				class="unstyled cursor-pointer hover:text-primary-500"
				data-testid="tablerow-detail-button"><i class="fa-solid fa-eye" /></Anchor
			>
		{/if}
		{#if displayEdit}
			<Anchor
				breadcrumbAction="push"
				label={m.edit()}
				href={editURL}
				stopPropagation
				class="unstyled cursor-pointer hover:text-primary-500"
				data-testid="tablerow-edit-button"><i class="fa-solid fa-pen-to-square" /></Anchor
			>
		{/if}
		{#if displayDelete}
			{#if URLModel === 'folders'}
				<button
					on:click={(_) => {
						promptModalConfirmDelete(row.meta[identifierField], row);
						stopPropagation(_);
					}}
					on:keydown={() => promptModalConfirmDelete(row.meta.id, row)}
					class="cursor-pointer hover:text-primary-500"
					data-testid="tablerow-delete-button"><i class="fa-solid fa-trash" /></button
				>
			{:else}
				<button
					on:click={(_) => {
						modalConfirmDelete(row.meta[identifierField], row);
						stopPropagation(_);
					}}
					on:keydown={() => modalConfirmDelete(row.meta.id, row)}
					class="cursor-pointer hover:text-primary-500"
					data-testid="tablerow-delete-button"><i class="fa-solid fa-trash" /></button
				>
			{/if}
		{/if}
	{/if}
	<slot name="tail" />
</span>

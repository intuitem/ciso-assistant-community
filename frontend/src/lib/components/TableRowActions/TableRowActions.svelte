<script lang="ts">
	import { page } from '$app/state';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import type { ModelMapEntry } from '$lib/utils/crud';
	import type { urlModel } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';

	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { canPerformAction } from '$lib/utils/access-control';
	import {
		getModalStore,
		type ModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		row: Record<string, any>;
		model?: ModelMapEntry;
		detailURL: string;
		editURL?: string;
		disableEdit?: boolean;
		disableView?: boolean;
		deleteForm?: SuperValidated<AnyZodObject> | null;
		URLModel?: urlModel | string;
		identifierField?: string;
		preventDelete?: boolean;
		preventEdit?: boolean;
		baseClass?: string;
		hasBody?: boolean;
		head?: import('svelte').Snippet;
		body?: import('svelte').Snippet;
		tail?: import('svelte').Snippet;
	}

	let {
		row,
		model = undefined,
		detailURL,
		editURL,
		disableEdit = false,
		disableView = false,
		deleteForm = null,
		URLModel,
		identifierField = 'id',
		preventDelete = false,
		preventEdit = false,
		baseClass = 'space-x-2 whitespace-nowrap flex flex-row items-center text-xl text-surface-700 justify-end',
		hasBody = false,
		head,
		body,
		tail
	}: Props = $props();

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
				: (row.name ?? row.meta.str ?? Object.values(row)[0]);
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
				? m.deleteUserMessage({ name: name as string })
				: m.deleteModalMessage({ name: name as string });
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.deleteModalTitle(),
			body: body
		};
		modalStore.trigger(modal);
	}

	const user = page.data.user;

	let canDeleteObject = $derived(
		!preventDelete &&
			(model
				? page.params.id
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
				: false)
	);
	let canEditObject = $derived(
		!preventEdit &&
			(model
				? page.params.id
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
				: false)
	);

	let displayDetail = $derived(detailURL && !disableView);
	let displayEdit = $derived(
		canEditObject &&
			!disableEdit &&
			URLModel &&
			!['frameworks', 'risk-matrices', 'ebios-rm'].includes(URLModel) &&
			editURL
	);
	let displayDelete = $derived(canDeleteObject && deleteForm !== null);
</script>

<span class={baseClass}>
	{@render head?.()}
	{@render body?.()}
	{#if !hasBody}
		{#if displayDetail}
			<Anchor
				breadcrumbAction="push"
				href={detailURL}
				class="unstyled cursor-pointer hover:text-primary-500"
				data-testid="tablerow-detail-button"><i class="fa-solid fa-eye"></i></Anchor
			>
		{/if}
		{#if URLModel === 'operating-modes'}
			<Anchor
				breadcrumbAction="push"
				label={m.graph()}
				href={`/operating-modes/${row.meta.id}/graph/`}
				stopPropagation
				class="unstyled cursor-pointer hover:text-primary-500"
				data-testid="tablerow-edit-button"><i class="fa-solid fa-project-diagram"></i></Anchor
			>
		{/if}
		{#if displayEdit}
			<Anchor
				breadcrumbAction="push"
				label={m.edit()}
				href={editURL}
				stopPropagation
				class="unstyled cursor-pointer hover:text-primary-500"
				data-testid="tablerow-edit-button"><i class="fa-solid fa-pen-to-square"></i></Anchor
			>
		{/if}
		{#if displayDelete}
			{#if URLModel === 'folders'}
				<button
					onclick={(e) => {
						promptModalConfirmDelete(row.meta[identifierField], row);
						stopPropagation(e);
					}}
					onkeydown={(e) => {
						if (e.key === 'Tab') return;
						modalConfirmDelete(row.meta.id, row);
						stopPropagation(e);
					}}
					class="cursor-pointer hover:text-primary-500"
					data-testid="tablerow-delete-button"><i class="fa-solid fa-trash"></i></button
				>
			{:else}
				<button
					onclick={(e) => {
						modalConfirmDelete(row.meta[identifierField], row);
						stopPropagation(e);
					}}
					onkeydown={(e) => {
						if (e.key === 'Tab') return;
						modalConfirmDelete(row.meta.id, row);
						stopPropagation(e);
					}}
					class="cursor-pointer hover:text-primary-500"
					data-testid="tablerow-delete-button"><i class="fa-solid fa-trash"></i></button
				>
			{/if}
		{/if}
	{/if}
	{@render tail?.()}
</span>

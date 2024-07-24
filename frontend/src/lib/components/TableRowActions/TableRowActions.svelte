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

	export let addOption: boolean = false;
	export let containerModel: object | undefined; // Find a better name for this prop N
	export let containerObject: { id: string; [key: string]: any } | undefined; // Find a better name for this prop ?
	export let containerReferences: Set<string>;
	let addLoading = false;
	let removeLoading = false;

	export let hasBody = false;

	function stopPropagation(event: Event): void {
		event.stopPropagation();
	}

	function modalConfirmDelete(id: string, name: string): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: deleteForm,
				id: id,
				debug: false,
				URLModel: URLModel
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.deleteModalTitle(),
			body: `${m.deleteModalMessage()}: ${name}?`
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

	const displayAdd =
		containerModel &&
		containerModel.reverseForeignKeyFields &&
		containerModel.reverseForeignKeyFields.filter(
			(field) => field.urlModel === model.urlModel && addOption
		).length > 0;
	let isInsideObject = containerReferences.has(row.id);
</script>

<span
	class="space-x-2 whitespace-nowrap flex flex-row items-center text-xl text-surface-700 justify-end"
>
	<slot name="head" />
	<slot name="body" />
	{#if !hasBody}
		{#if displayAdd && containerObject}
			{#if isInsideObject}
				<button
					class="cursor-pointer hover:text-primary-500"
					on:click={(e) => {
						const formData = new FormData();
						formData.append('evidence', row.id);
						addLoading = true;

						fetch(`/applied_controls/${containerObject.id}?/remove_evidence`, {
							method: 'POST',
							body: formData
						}).then((res) => {
							if (res.ok) {
								isInsideObject = false;
							} else {
								removeLoading = false;
							}
						});
						e.stopPropagation();
					}}
				>
					{#if removeLoading}
						<div class="flex items-center cursor-progress" role="status">
							<svg
								aria-hidden="true"
								class="w-5 h-5 text-gray-200 animate-spin dark:text-gray-600 fill-primary-500"
								viewBox="0 0 100 101"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
							>
								<path
									d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
									fill="currentColor"
								/>
								<path
									d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
									fill="currentFill"
								/>
							</svg>
						</div>
					{:else}
						<i class="fa-solid fa-square-minus" />
					{/if}
				</button>
			{:else}
				<button
					class="cursor-pointer hover:text-primary-500"
					on:click={(e) => {
						const formData = new FormData();
						formData.append('evidence', row.id);
						addLoading = true;

						fetch(`/applied_controls/${containerObject.id}?/add_evidence`, {
							method: 'POST',
							body: formData
						}).then((res) => {
							if (res.ok) {
								isInsideObject = true;
							} else {
								addLoading = false;
							}
						});
						e.stopPropagation();
					}}
				>
					{#if addLoading}
						<div class="flex items-center cursor-progress" role="status">
							<svg
								aria-hidden="true"
								class="w-5 h-5 text-gray-200 animate-spin dark:text-gray-600 fill-primary-500"
								viewBox="0 0 100 101"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
							>
								<path
									d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
									fill="currentColor"
								/>
								<path
									d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
									fill="currentFill"
								/>
							</svg>
						</div>
					{:else}
						<i class="fa-solid fa-plus" />
					{/if}
				</button>
			{/if}
		{/if}
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
					modalConfirmDelete(row.meta[identifierField], row.name ?? Object.values(row)[0]);
					stopPropagation(_);
				}}
				on:keydown={(_) => modalConfirmDelete(row.meta.id, row.name ?? Object.values(row)[0])}
				class="cursor-pointer hover:text-primary-500"
				data-testid="tablerow-delete-button"><i class="fa-solid fa-trash" /></button
			>
		{/if}
	{/if}
	<slot name="tail" />
</span>

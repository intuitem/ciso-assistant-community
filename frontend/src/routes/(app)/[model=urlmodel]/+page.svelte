<script lang="ts">
	import { page } from '$app/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type {
		ModalComponent,
		ModalSettings,
		ModalStore,
		ToastStore
	} from '@skeletonlabs/skeleton';
	import { getModalStore, getToastStore } from '@skeletonlabs/skeleton';
	import { superForm } from 'sveltekit-superforms/client';
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	import { localItems, getDeterminant } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let data: PageData;

	const modalStore: ModalStore = getModalStore();
	const toastStore: ToastStore = getToastStore();

	function handleFormUpdated({
		form,
		pageStatus,
		closeModal
	}: {
		form: any;
		pageStatus: number;
		closeModal: boolean;
	}) {
		if (closeModal && form.valid) {
			$modalStore[0] ? modalStore.close() : null;
		}
		if (form.message) {
			const toast: { message: string; background: string } = {
				message: form.message,
				background: pageStatus === 200 ? 'variant-filled-success' : 'variant-filled-error'
			};
			toastStore.trigger(toast);
		}
	}

	let { form: deleteForm, message: deleteMessage } = {
		form: {},
		message: {}
	};

	let { form: createForm, message: createMessage } = {
		form: {},
		message: {}
	};

	// NOTE: This is a workaround for an issue we had with getting the return value from the form actions after switching pages in route /[model=urlmodel]/ without a full page reload.
	// invalidateAll() did not work.
	$: {
		({ form: createForm, message: createMessage } = superForm(data.createForm, {
			onUpdated: ({ form }) =>
				handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
		}));
		({ form: deleteForm, message: deleteMessage } = superForm(data.deleteForm, {
			onUpdated: ({ form }) =>
				handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
		}));
	}

	function modalCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.createForm,
				model: data.model,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: `New ${data.model.verboseName}`
		};
		modalStore.trigger(modal);
	}

	$: search = data.model?.search !== false;
</script>

{#if data.table}
	<div class="shadow-lg">
		<ModelTable source={data.table} deleteForm={data.deleteForm} URLModel={data.URLModel} {search}>
			<div slot="addButton">
				{#if !['risk-matrices', 'frameworks', 'user-groups', 'role-assignments'].includes(data.URLModel)}
					<button
						class="btn variant-filled-primary self-end"
						data-testid="add-button"
						on:click={modalCreateForm}
						><i class="fa-solid fa-plus mr-2" />
						{m.addButton({determinant:getDeterminant(languageTag(), "undefined", data.model), model: localItems(languageTag())[data.model.localName].toLowerCase()})}
					</button
					>
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

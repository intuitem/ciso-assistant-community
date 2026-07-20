<script lang="ts">
	import { page } from '$app/state';

	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ServiceAccountSecretModal from '$lib/components/Modals/ServiceAccountSecretModal.svelte';
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

	function modalSecret(object: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: ServiceAccountSecretModal,
			props: {
				clientId: object.client_id,
				clientSecret: object.client_secret
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.clientSecret()
		};
		modalStore.trigger(modal);
	}

	// The create action returns the written object, which carries the one-time
	// client_secret. Show it once, after the create modal has closed.
	let displayedSecretForId = $state('');
	$effect(() => {
		const object = (form as Record<string, any> | null)?.form?.message?.object;
		if (object?.client_secret && object.id !== displayedSecretForId) {
			displayedSecretForId = object.id;
			setTimeout(() => modalSecret(object), 0);
		}
	});
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
			<ModelTable source={data.table} deleteForm={data.deleteForm} {URLModel} />
		{/key}
	</div>
{/if}

<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import type { ModalComponent, ModalSettings } from '@skeletonlabs/skeleton-svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import List from '$lib/components/List/List.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	async function modalConfirmSyncAppliedControls() {
		const referenceControlId = page.params.id;

		const endpoint = `/reference-controls/${referenceControlId}/syncable-applied-controls`;
		const syncableAppliedControls = await fetch(endpoint).then((response) => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error('Failed to fetch syncable reference controls.');
			}
		});

		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: data.form,
				id: referenceControlId,
				URLModel: 'reference-controls',
				formAction: '?/syncAppliedControls',
				bodyComponent: List,
				bodyProps: {
					items: syncableAppliedControls.map((appliedControl) => appliedControl.name),
					message: m.confirmModalMessagePlural()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.syncToAppliedControls(),
			body: m.syncAppliedControlsMessage()
		};
		modalStore.trigger(modal);
	}
</script>

<DetailView {data}>
	{#snippet widgets()}
		<button
			class="btn text-gray-100 bg-linear-to-r from-sky-500 to-cyan-500 h-fit"
			data-testid="sync-to-actions-button"
			onclick={async () => {
				await modalConfirmSyncAppliedControls();
			}}
		>
			<span class="mr-2">
				<i class="fa-solid fa-arrows-rotate mr-2"></i>
			</span>
			{m.syncToAppliedControls()}
		</button>
	{/snippet}
</DetailView>

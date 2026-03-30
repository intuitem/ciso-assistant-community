<script lang="ts">
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import type { ModalComponent, ModalSettings } from '@skeletonlabs/skeleton-svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import List from '$lib/components/List/List.svelte';

	interface LocalPageData extends PageData {
		dryRunData: [string, string][];
	}

	interface Props {
		data: LocalPageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	async function modalConfirmSyncAppliedControls() {
		const appliedControlId = page.params.id;

		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: data.form,
				id: appliedControlId,
				URLModel: 'reference-controls',
				formAction: '?/syncAppliedControls',
				bodyComponent: List,
				bodyProps: {
					items: dryRunData.map(
						([oldValue, newValue]) => `${safeTranslate(oldValue)} ➡️ ${safeTranslate(newValue)}`
					),
					message: m.theFollowingChangesWillBeApplied()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.syncToReferenceControl(),
			body: ''
		};
		modalStore.trigger(modal);
	}

	let dryRunData: [string, string][] = $derived(data.dryRunData);
</script>

<DetailView {data}>
	{#snippet actions()}
		{#if dryRunData.length > 0}
			<button
				class="btn preset-filled-primary-500 h-fit"
				data-testid="sync-to-actions-button"
				onclick={async () => {
					await modalConfirmSyncAppliedControls();
				}}
			>
				<i class="fa-solid fa-arrows-rotate mr-2"></i>
				{m.syncToReferenceControl()}
			</button>
		{/if}
	{/snippet}
</DetailView>

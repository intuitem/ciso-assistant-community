<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';
	import { safeTranslate } from '$lib/utils/i18n';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { page } from '$app/state';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { enhance } from '$app/forms';

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const URLModel = data.URLModel;
	let syncing = $state(false);

	// Check if we should auto-sync on page load
	$effect(() => {
		if (data.riskAssessmentToSync) {
			// Auto-trigger sync for the specific risk assessment
			syncRiskAssessment(data.riskAssessmentToSync.id);
			// Clean URL
			window.history.replaceState({}, '', window.location.pathname);
		}
	});

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

	async function syncRiskAssessment(riskAssessmentId?: string) {
		syncing = true;
		const idToSync = riskAssessmentId || data.lastRiskAssessment?.id;

		if (!idToSync) {
			toastStore.trigger({
				message: 'No risk assessment to sync',
				background: 'variant-filled-error',
				timeout: 5000
			});
			syncing = false;
			return;
		}

		try {
			const formData = new FormData();
			formData.append('risk_assessment_id', idToSync);

			const response = await fetch('?/sync', {
				method: 'POST',
				body: formData
			});

			const result = await response.json();
			console.log('Sync response:', result); // Debug log

			// SvelteKit wraps action responses in a specific structure
			if (result.type === 'success' || result.data?.success) {
				const actionData = result.data || result;
				toastStore.trigger({
					message: actionData.message || 'Synchronization complete',
					background: 'variant-filled-success',
					timeout: 5000
				});
				// Redirect to the risk assessment
				setTimeout(() => {
					window.location.href = `/risk-assessments/${idToSync}`;
				}, 1000);
			} else {
				const actionData = result.data || result;
				toastStore.trigger({
					message: actionData.message || 'Synchronization failed',
					background: 'variant-filled-error',
					timeout: 5000
				});
			}
		} catch (error) {
			console.error('Sync error:', error);
			toastStore.trigger({
				message: 'An error occurred during synchronization',
				background: 'variant-filled-error',
				timeout: 5000
			});
		} finally {
			syncing = false;
		}
	}
</script>

<ModelTable
	source={data.table}
	deleteForm={data.deleteForm}
	{URLModel}
	baseEndpoint="/risk-assessments/?ebios_rm_study={page.params.id}"
>
	{#snippet addButton()}
		<div class="flex gap-2">
			{#if data.lastRiskAssessment}
				<!-- Sync button when risk assessment exists -->
				<button
					class="btn btn-sm variant-filled-secondary"
					onclick={() => syncRiskAssessment()}
					disabled={syncing}
					title="Synchronize existing risk assessment with EBIOS RM"
				>
					<i class="fa-solid fa-sync {syncing ? 'fa-spin' : ''}"></i>
					<span>{syncing ? 'Syncing...' : 'Sync from EBIOS RM'}</span>
				</button>
			{/if}

			<!-- Create new button (always visible) -->
			<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
				<button
					class="inline-block p-3 btn-mini-primary w-12 focus:relative"
					data-testid="add-button"
					title={safeTranslate('add-' + data.model.localName)}
					onclick={modalCreateForm}
					disabled={syncing}
					><i class="fa-solid fa-file-circle-plus"></i>
				</button>
			</span>
		</div>
	{/snippet}
</ModelTable>

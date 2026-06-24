<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { getModalStore } from '$lib/components/Modals/stores';
	import { openRiskAcceptanceModal } from '$lib/utils/riskAcceptance';

	interface Props {
		meta: any;
	}

	let { meta }: Props = $props();

	const modalStore = getModalStore();
	const canCreate = Object.hasOwn(page.data.user?.permissions ?? {}, 'add_riskacceptance');
	// Mirror the detail page: no acceptance requests on a locked assessment.
	const isLocked = $derived(meta.risk_assessment?.is_locked ?? false);

	function createAcceptance(): void {
		openRiskAcceptanceModal(modalStore, {
			folderId: meta.folder?.id ?? meta.folder,
			riskScenarioIds: [meta.id]
		});
	}
</script>

{#if canCreate && !isLocked}
	<button
		onclick={(e) => {
			e.stopPropagation();
			createAcceptance();
		}}
		class="cursor-pointer hover:text-primary-500"
		aria-label={m.requestRiskAcceptance()}
		title={m.requestRiskAcceptance()}
		data-testid="tablerow-create-acceptance-button"
	>
		<i class="fa-solid fa-signature"></i>
	</button>
{/if}

<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { getModelInfo } from '$lib/utils/crud';
	import { modelSchema } from '$lib/utils/schemas';
	import { defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	interface Props {
		meta: any;
		actionsURLModel: string;
	}

	let { meta }: Props = $props();

	const modalStore = getModalStore();
	const canCreate = Object.hasOwn(page.data.user?.permissions ?? {}, 'add_riskacceptance');

	function createAcceptance(): void {
		const schema = modelSchema('risk-acceptances');
		// Pre-fill the new acceptance with this scenario and its domain; the
		// approver is left empty (usually not the scenario owner).
		const form = defaults(
			{ folder: meta.folder?.id ?? meta.folder, risk_scenarios: [meta.id] },
			zod(schema)
		);
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form,
				model: getModelInfo('risk-acceptances'),
				formAction: '/risk-acceptances?/create',
				invalidateAll: true,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.requestRiskAcceptance()
		};
		modalStore.trigger(modal);
	}
</script>

{#if canCreate}
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

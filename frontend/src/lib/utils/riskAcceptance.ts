import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaults } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import CreateModal from '$lib/components/Modals/CreateModal.svelte';
import { m } from '$paraglide/messages';
import type { ModalStore, ModalComponent, ModalSettings } from '$lib/components/Modals/stores';

interface RiskAcceptancePrefill {
	folderId?: string;
	riskScenarioIds: string[];
}

/**
 * Open the "request risk acceptance" create modal, pre-filled with the given
 * scenario(s) and domain. The approver is intentionally left empty (usually not
 * the scenario owner). Single source of truth for the prefill shape, shared by
 * the scenario detail page and the scenario table row action.
 */
export function openRiskAcceptanceModal(
	modalStore: ModalStore,
	{ folderId, riskScenarioIds }: RiskAcceptancePrefill
): void {
	const schema = modelSchema('risk-acceptances');
	const form = defaults({ folder: folderId, risk_scenarios: riskScenarioIds }, zod(schema));
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

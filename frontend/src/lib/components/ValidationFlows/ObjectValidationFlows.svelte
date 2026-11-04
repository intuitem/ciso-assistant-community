<script lang="ts">
	import { page } from '$app/state';
	import { refreshAll } from '$app/navigation';
	import { m } from '#paraglide/messages.js';
	import CreateModal from '#lib/components/Modals/CreateModal.svelte';
	import { getModalStore, type ModalStore } from '#lib/components/Modals/stores.js';
	import ValidationFlowsSection from './ValidationFlowsSection.svelte';

	/** Request-validation button and the flows of one object, for pages not built on DetailView. */
	interface Props {
		form: any;
		model: any;
		flows: any[];
	}

	let { form, model, flows }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	function requestValidation(): void {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: CreateModal,
				props: {
					form,
					model,
					debug: false,
					invalidateAll: true,
					formAction: '/validation-flows?/create',
					onConfirm: async () => {
						await refreshAll();
					}
				}
			},
			title: m.requestValidation()
		});
	}
</script>

{#if page.data?.featureflags?.validation_flows && form}
	<div class="flex flex-col gap-2">
		<button
			class="btn text-gray-100 bg-linear-to-r from-orange-500 to-amber-500 h-fit"
			onclick={requestValidation}
			data-testid="request-validation-button"
		>
			<i class="fa-solid fa-check-circle mr-2"></i>{m.requestValidation()}
		</button>
		{#if flows?.length}
			{#key flows}
				<ValidationFlowsSection validationFlows={flows} />
			{/key}
		{/if}
	</div>
{/if}

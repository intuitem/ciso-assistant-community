<script lang="ts">
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface ProblematicScenario {
		id: string;
		name: string;
		ref_id: string;
		residual_hypotheses_count: number;
		residual_hypotheses: Array<{
			id: string;
			name: string;
			is_selected: boolean;
		}>;
	}

	function closeModal() {
		modalStore.close();
	}

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
</script>

{#if $modalStore[0]}
	{@const scenarios = $modalStore[0].meta?.scenarios || []}
	<div class={cBase}>
		<header class={cHeader}>Unprocessed Scenarios</header>
		<p class="text-surface-600">
			The following scenarios have multiple residual hypotheses. Please select one residual
			hypothesis per scenario to include it in the action plan.
		</p>

		<section>
			{#if scenarios && scenarios.length > 0}
				<div class="space-y-4">
					{#each scenarios as scenario}
						<div class="card variant-ghost-warning p-4">
							<div class="flex items-center justify-between mb-3">
								<div>
									<h4 class="h4 font-semibold">
										{scenario.ref_id}: {scenario.name}
									</h4>
									<p class="text-sm text-surface-600">
										{scenario.residual_hypotheses_count} residual hypotheses found
									</p>
								</div>
							</div>

							<div class="space-y-2">
								<p class="text-sm font-medium">Residual Hypotheses:</p>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
									{#each scenario.residual_hypotheses as hypothesis}
										<div
											class="flex items-center space-x-2 p-2 rounded-lg {hypothesis.is_selected
												? 'bg-success-100 border border-success-300'
												: 'bg-surface-100'}"
										>
											<div class="flex-1">
												<p class="font-medium text-sm">{hypothesis.name}</p>
											</div>
											{#if hypothesis.is_selected}
												<span class="badge variant-filled-success text-xs">Selected</span>
											{:else}
												<span class="badge variant-soft-surface text-xs">Not Selected</span>
											{/if}
										</div>
									{/each}
								</div>
							</div>

							<div class="mt-3 p-3 bg-warning-100 border border-warning-300 rounded-lg">
								<p class="text-sm text-warning-800">
									<i class="fas fa-exclamation-triangle mr-1"></i>
									To resolve this, go to the scenario and ensure only one residual hypothesis is selected.
								</p>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-center py-8">
					<p class="text-surface-600">No problematic scenarios found.</p>
				</div>
			{/if}
		</section>

		<footer class="flex justify-end pt-4">
			<button type="button" class="btn variant-filled" onclick={closeModal}> Close </button>
		</footer>
	</div>
{/if}

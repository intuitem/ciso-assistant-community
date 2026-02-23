<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { m } from '$paraglide/messages';
	import type { RiskMatrixJsonDefinition } from '$lib/utils/types';
	import { enhance } from '$app/forms';

	let { data, form } = $props();

	const toastStore = getToastStore();
	const risk_assessment = data.risk_assessment;
	const parsedMatrix: RiskMatrixJsonDefinition = JSON.parse(
		risk_assessment.risk_matrix.json_definition
	);

	// Parse probability and impact options from the matrix
	const probabilityOptions = parsedMatrix.probability;
	const impactOptions = parsedMatrix.impact;

	// State for anchoring values
	let probabilityAnchors: Record<number, string> = $state({});
	let impactAnchors: Record<number, string> = $state({});
	let lossThreshold: string = $state('');
	let isSubmitting = $state(false);

	// Initialize anchoring dictionaries
	probabilityOptions.forEach((_, index) => {
		probabilityAnchors[index] = '';
	});

	impactOptions.forEach((_, index) => {
		impactAnchors[index] = '';
	});

	// Handle form result
	$effect(() => {
		if (form?.success) {
			toastStore.trigger({
				message: m.conversionSuccessful(),
				background: 'variant-filled-success'
			});
			// Redirect to the newly created quantitative risk study
			goto(`/quantitative-risk-studies/${form.quantitative_risk_study_id}`);
		} else if (form?.error) {
			toastStore.trigger({
				message: form.error,
				background: 'variant-filled-error'
			});
			isSubmitting = false;
		}
	});

	function validateAndPrepareData(): object | null {
		// Validate that ALL probability values are provided
		const missingProbabilities = probabilityOptions.filter((_, index) => {
			return !probabilityAnchors[index] || probabilityAnchors[index] === '';
		});

		if (missingProbabilities.length > 0) {
			toastStore.trigger({
				message: m.allProbabilityValuesMustBeProvided(),
				background: 'variant-filled-error'
			});
			return null;
		}

		// Validate that ALL impact values are provided
		const missingImpacts = impactOptions.filter((_, index) => {
			return !impactAnchors[index] || impactAnchors[index] === '';
		});

		if (missingImpacts.length > 0) {
			toastStore.trigger({
				message: m.allImpactValuesMustBeProvided(),
				background: 'variant-filled-error'
			});
			return null;
		}

		// Validate probability values (must be between 0 and 100, exclusive)
		for (let index = 0; index < probabilityOptions.length; index++) {
			const value = parseFloat(probabilityAnchors[index]);
			if (isNaN(value) || value <= 0 || value >= 100) {
				toastStore.trigger({
					message: m.probabilityMustBeBetweenZeroAndHundred({
						level: probabilityOptions[index].name
					}),
					background: 'variant-filled-error'
				});
				return null;
			}
		}

		// Validate that probability values are increasing
		for (let i = 1; i < probabilityOptions.length; i++) {
			const currentValue = parseFloat(probabilityAnchors[i]);
			const previousValue = parseFloat(probabilityAnchors[i - 1]);

			if (currentValue <= previousValue) {
				toastStore.trigger({
					message: m.probabilityValuesMustBeIncreasing({
						current: probabilityOptions[i].name,
						previous: probabilityOptions[i - 1].name
					}),
					background: 'variant-filled-error'
				});
				return null;
			}
		}

		// Validate impact values (must be > 0)
		for (let index = 0; index < impactOptions.length; index++) {
			const value = parseFloat(impactAnchors[index]);
			if (isNaN(value) || value <= 0) {
				toastStore.trigger({
					message: m.impactMustBeGreaterThanZero({
						level: impactOptions[index].name
					}),
					background: 'variant-filled-error'
				});
				return null;
			}
		}

		// Validate that impact values are increasing
		for (let i = 1; i < impactOptions.length; i++) {
			const currentValue = parseFloat(impactAnchors[i]);
			const previousValue = parseFloat(impactAnchors[i - 1]);

			if (currentValue <= previousValue) {
				toastStore.trigger({
					message: m.impactValuesMustBeIncreasing({
						current: impactOptions[i].name,
						previous: impactOptions[i - 1].name
					}),
					background: 'variant-filled-error'
				});
				return null;
			}
		}

		// Validate loss threshold (mandatory)
		if (!lossThreshold || parseFloat(lossThreshold) <= 0) {
			toastStore.trigger({
				message: m.pleaseProvideValidLossThreshold(),
				background: 'variant-filled-error'
			});
			return null;
		}

		// Prepare conversion payload
		return {
			probability_anchors: Object.entries(probabilityAnchors)
				.filter(([_, value]) => value !== '')
				.map(([index, value]) => ({
					index: parseInt(index),
					value: parseFloat(value) / 100 // Convert percentage to probability (0-1)
				})),
			impact_anchors: Object.entries(impactAnchors)
				.filter(([_, value]) => value !== '')
				.map(([index, value]) => ({
					index: parseInt(index),
					central_value: parseFloat(value)
				})),
			loss_threshold: parseFloat(lossThreshold)
		};
	}
</script>

<main class="grow main relative">
	<!-- Loading overlay for Monte Carlo simulations -->
	{#if isSubmitting}
		<div
			class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
			style="backdrop-filter: blur(4px);"
		>
			<div class="card bg-white p-8 shadow-xl max-w-md text-center space-y-4">
				<Progress value={null}>
					<Progress.Circle class="[--size:--spacing(16)] mx-auto">
						<Progress.CircleTrack />
						<Progress.CircleRange class="stroke-primary-500" />
					</Progress.Circle>
				</Progress>
				<h3 class="text-xl font-bold">{m.converting()}</h3>
				<p class="text-gray-600">
					{m.runningMonteCarloSimulations()}
				</p>
			</div>
		</div>
	{/if}

	<div class="card bg-white p-6 m-4 shadow-sm">
		<div class="mb-6">
			<h2 class="text-2xl font-bold">{m.convertToQuantitativeRisk()}</h2>
			<p class="text-gray-600 mt-2">
				{m.convertToQuantitativeRiskDescription()}
			</p>
		</div>

		<div class="space-y-6">
			<!-- Risk Assessment Info -->
			<div class="p-4 bg-gray-50 rounded-lg">
				<h3 class="font-semibold mb-2">{m.sourceRiskAssessment()}</h3>
				<p class="text-sm">
					<span class="font-medium">{m.name()}:</span>
					{risk_assessment.name}
				</p>
				<p class="text-sm">
					<span class="font-medium">{m.domain()}:</span>
					{risk_assessment.folder.str}
				</p>
				<p class="text-sm">
					<span class="font-medium">{m.riskMatrix()}:</span>
					{risk_assessment.risk_matrix.name}
				</p>
			</div>

			<!-- Probability Anchoring -->
			<div class="space-y-4">
				<h3 class="text-lg font-semibold">{m.probabilityAnchoring()}</h3>
				<p class="text-sm text-gray-600">{m.probabilityAnchoringDescription()}</p>
				<div
					class="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800 flex items-start space-x-2"
				>
					<i class="fa-solid fa-info-circle mt-0.5"></i>
					<div>
						<strong>{m.requirements()}</strong>
						{m.probabilityRequirements()}
					</div>
				</div>
				<div class="space-y-3 max-w-2xl">
					{#each probabilityOptions as prob, index}
						<div
							class="flex items-center space-x-4 p-3 bg-gray-50 rounded-lg border border-gray-200"
						>
							<div
								class="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-700 rounded-full font-semibold text-sm"
							>
								{index + 1}
							</div>
							{#if prob.hexcolor}
								<div
									class="w-6 h-6 rounded border border-gray-300"
									style="background-color: {prob.hexcolor};"
									title="{prob.name} color"
								></div>
							{/if}
							<label class="flex-1 font-medium text-sm" for="prob-{index}">
								{prob.name}
								{#if prob.description}
									<span class="text-xs text-gray-500 block mt-1">{prob.description}</span>
								{/if}
							</label>
							<input
								id="prob-{index}"
								type="number"
								step="0.1"
								min="0.1"
								max="99.9"
								bind:value={probabilityAnchors[index]}
								class="input w-32"
								placeholder="0 - 100 %"
								required
							/>
						</div>
					{/each}
				</div>
			</div>

			<!-- Impact Anchoring -->
			<div class="space-y-4">
				<h3 class="text-lg font-semibold">{m.impactAnchoring()}</h3>
				<p class="text-sm text-gray-600">{m.impactAnchoringDescription()}</p>
				<div
					class="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800 flex items-start space-x-2"
				>
					<i class="fa-solid fa-info-circle mt-0.5"></i>
					<div>
						<strong>{m.requirements()}</strong>
						{m.impactRequirements()}
					</div>
				</div>
				<div class="space-y-3 max-w-2xl">
					{#each impactOptions as impact, index}
						<div
							class="flex items-center space-x-4 p-3 bg-gray-50 rounded-lg border border-gray-200"
						>
							<div
								class="flex items-center justify-center w-8 h-8 bg-green-100 text-green-700 rounded-full font-semibold text-sm"
							>
								{index + 1}
							</div>
							{#if impact.hexcolor}
								<div
									class="w-6 h-6 rounded border border-gray-300"
									style="background-color: {impact.hexcolor};"
									title="{impact.name} color"
								></div>
							{/if}
							<label class="flex-1 font-medium text-sm" for="impact-{index}">
								{impact.name}
								{#if impact.description}
									<span class="text-xs text-gray-500 block mt-1">{impact.description}</span>
								{/if}
							</label>
							<input
								id="impact-{index}"
								type="number"
								step="1000"
								min="1"
								bind:value={impactAnchors[index]}
								class="input w-40"
								placeholder="e.g., 25000"
								required
							/>
						</div>
					{/each}
				</div>
			</div>

			<!-- Loss Threshold -->
			<div class="space-y-2">
				<h3 class="text-lg font-semibold">{m.lossThreshold()}</h3>
				<p class="text-sm text-gray-600">{m.lossThresholdDescription()}</p>
				<input
					type="number"
					step="1000"
					min="1"
					bind:value={lossThreshold}
					class="input max-w-md"
					placeholder="e.g., 100000"
					required
				/>
			</div>

			<!-- Action Buttons -->
			<form
				method="POST"
				use:enhance={() => {
					const payload = validateAndPrepareData();
					if (!payload) {
						return async ({ update }) => {
							await update({ reset: false });
						};
					}

					isSubmitting = true;

					return async ({ result, update }) => {
						await update();
						if (result.type !== 'success') {
							isSubmitting = false;
						}
					};
				}}
			>
				<input type="hidden" name="data" value="" />
				<div class="flex space-x-4 pt-4 border-t">
					<button
						type="submit"
						class="btn preset-filled-primary-500"
						disabled={isSubmitting}
						onclick={(e) => {
							const payload = validateAndPrepareData();
							if (!payload) {
								e.preventDefault();
								return;
							}
							const form = e.currentTarget.closest('form');
							if (form) {
								const input = form.querySelector('input[name="data"]');
								if (input) {
									input.value = JSON.stringify(payload);
								}
							}
						}}
					>
						{#if isSubmitting}
							<Progress value={null}>
								<Progress.Circle class="[--size:--spacing(6)]">
									<Progress.CircleTrack />
									<Progress.CircleRange class="stroke-white" />
								</Progress.Circle>
							</Progress>
							<span class="ml-2">{m.converting()}</span>
						{:else}
							<i class="fa-solid fa-exchange-alt mr-2"></i>
							{m.convertToQuantitative()}
						{/if}
					</button>
					<button
						type="button"
						class="btn preset-outlined"
						onclick={() => goto(`/risk-assessments/${risk_assessment.id}`)}
						disabled={isSubmitting}
					>
						<i class="fa-solid fa-arrow-left mr-2"></i>
						{m.cancel()}
					</button>
				</div>
			</form>
		</div>
	</div>
</main>

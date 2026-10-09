<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data }: Props = $props();

	const dpia = $derived(data.data);
	const missing = $derived(new Set<string>(data.report?.missing ?? []));
	const hasRegisters = $derived(dpia.design_risk_assessment && dpia.incident_risk_assessment);

	const checklist = [
		{ key: 'reasons', label: m.reasons() },
		{ key: 'purposes', label: m.purposes() },
		{ key: 'personal_data', label: m.personalData() },
		{ key: 'data_subjects', label: m.dataSubjects() },
		{ key: 'supporting_assets', label: m.supportingAssets() },
		{ key: 'necessity', label: m.necessity() },
		{ key: 'proportionality', label: m.proportionality() },
		{ key: 'design_risk_assessment', label: m.designRiskAssessment() },
		{ key: 'incident_risk_assessment', label: m.incidentRiskAssessment() },
		{ key: 'method_statement', label: m.methodStatement() },
		{ key: 'dpo_opinion', label: m.dpoOpinion() },
		{ key: 'data_subject_views', label: m.dataSubjectViews() },
		{ key: 'decision', label: m.decision() }
	];

	const done = $derived(checklist.filter((item) => !missing.has(item.key)).length);
	let selectedMatrix = $state('');
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<a
				href="/dpias/{dpia.id}/report"
				class="btn preset-filled-primary-500 h-fit"
				data-testid="dpia-report-button"
			>
				<i class="fa-solid fa-file-lines mr-2"></i>
				{m.dpiaReport()}
			</a>
			{#if !hasRegisters}
				<form
					method="POST"
					action="?/createRiskRegisters"
					use:enhance
					class="flex flex-col space-y-2 card p-3 preset-tonal"
				>
					<label class="text-sm font-semibold" for="dpia-risk-matrix">{m.riskMatrix()}</label>
					<select
						id="dpia-risk-matrix"
						name="risk_matrix"
						class="select"
						bind:value={selectedMatrix}
						required
					>
						<option value="" disabled>--</option>
						{#each data.riskMatrices as matrix}
							<option value={matrix.id}>{matrix.name}</option>
						{/each}
					</select>
					<button type="submit" class="btn preset-filled-secondary-500" disabled={!selectedMatrix}>
						<i class="fa-solid fa-shield-halved mr-2"></i>
						{m.dpiaCreateRiskRegisters()}
					</button>
				</form>
			{/if}
		</div>
	{/snippet}

	{#snippet widgets()}
		{#if data.report}
			<div class="card p-4 bg-surface-50-950 shadow-sm flex flex-col gap-3">
				<div class="flex items-baseline justify-between">
					<h3 class="font-semibold">{m.dpiaCompleteness()}</h3>
					<span class="text-sm text-surface-500">{done} / {checklist.length}</span>
				</div>
				<div class="h-2 rounded bg-surface-200-800 overflow-hidden">
					<div
						class="h-full bg-primary-500"
						style="width: {(done / checklist.length) * 100}%"
					></div>
				</div>
				<ul class="flex flex-col gap-1 text-sm">
					{#each checklist as item}
						<li class="flex items-center gap-2">
							{#if missing.has(item.key)}
								<i class="fa-regular fa-circle text-surface-400-600"></i>
								<span class="text-surface-600-400">{item.label}</span>
							{:else}
								<i class="fa-solid fa-circle-check text-success-600"></i>
								<span>{item.label}</span>
							{/if}
						</li>
					{/each}
				</ul>
				{#if dpia.decision}
					<p class="text-sm">
						<span class="font-semibold">{m.decision()}:</span>
						{safeTranslate(dpia.decision)}
					</p>
				{/if}
			</div>
		{/if}
	{/snippet}
</DetailView>

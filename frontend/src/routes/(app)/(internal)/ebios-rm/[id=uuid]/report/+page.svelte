<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('EBIOS RM Study Report');

	const { reportData } = data;
	const study = reportData.study;
</script>

<div class="bg-white shadow-sm p-8 max-w-7xl mx-auto">
	<!-- Back to Study Link -->
	<div class="mb-4">
		<Anchor
			breadcrumbAction="push"
			href={`/ebios-rm/${study.id}`}
			class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<p>{m.backToStudy()}</p>
		</Anchor>
	</div>

	<!-- Study Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">{study.name}</h1>
		{#if study.description}
			<p class="text-gray-600 mb-4">{study.description}</p>
		{/if}
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
			<div>
				<span class="font-semibold text-gray-700">{m.version()}:</span>
				<span class="ml-2">{study.version || 'N/A'}</span>
			</div>
			<div>
				<span class="font-semibold text-gray-700">{m.status()}:</span>
				<span class="ml-2">{study.status ? safeTranslate(study.status) : 'N/A'}</span>
			</div>
			<div>
				<span class="font-semibold text-gray-700">{m.eta()}:</span>
				<span class="ml-2">{study.eta ? formatDateOrDateTime(study.eta) : 'N/A'}</span>
			</div>
			<div>
				<span class="font-semibold text-gray-700">{m.dueDate()}:</span>
				<span class="ml-2">{study.due_date ? formatDateOrDateTime(study.due_date) : 'N/A'}</span>
			</div>
		</div>
	</div>

	<!-- Feared Events Section -->
	{#if reportData.feared_events.length > 0}
		<section class="mb-8">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.fearedEvents()} ({reportData.feared_events.length})
			</h2>
			<div class="space-y-4">
				{#each reportData.feared_events as event}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">{event.name}</h3>
						<div class="flex flex-wrap gap-4 text-sm mb-3">
							<div>
								<span class="font-semibold text-gray-700">{m.gravity()}:</span>
								<span
									class="ml-2 px-2 py-1 rounded"
									style="background-color: {event.gravity.hexcolor}"
								>
									{safeTranslate(event.gravity.name)}
								</span>
							</div>
							{#if event.assets.length > 0}
								<div>
									<span class="font-semibold text-gray-700">{m.assets()}:</span>
									<span class="ml-2">{event.assets.map((a) => a.str).join(', ')}</span>
								</div>
							{/if}
							{#if event.qualifications.length > 0}
								<div>
									<span class="font-semibold text-gray-700">{m.qualifications()}:</span>
									<span class="ml-2">{event.qualifications.map((q) => q.str).join(', ')}</span>
								</div>
							{/if}
						</div>
						{#if event.description}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.description()}:</span>
								<p class="mt-1 text-gray-600">{event.description}</p>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- RO/TO Couples Section -->
	{#if reportData.ro_to_couples.length > 0}
		<section class="mb-8">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.roToCouples()} ({reportData.ro_to_couples.length})
			</h2>
			<div class="space-y-4">
				{#each reportData.ro_to_couples as roto}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">
							{safeTranslate(roto.risk_origin)} - {roto.target_objective}
						</h3>
						<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
							<div>
								<span class="font-semibold text-gray-700">{m.motivation()}:</span>
								<span class="ml-2">{safeTranslate(roto.motivation)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.resources()}:</span>
								<span class="ml-2">{safeTranslate(roto.resources)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.activity()}:</span>
								<span class="ml-2">{safeTranslate(roto.activity)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.pertinence()}:</span>
								<span class="ml-2">{safeTranslate(roto.pertinence)}</span>
							</div>
						</div>
						{#if roto.feared_events.length > 0}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.fearedEvents()}:</span>
								<span class="ml-2 text-gray-600"
									>{reportData.feared_events
										.filter((fe) => roto.feared_events.some((id) => id.id === fe.id))
										.map((fe) => fe.name)
										.join(', ')}</span
								>
							</div>
						{/if}
						{#if roto.justification}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.justification()}:</span>
								<span class="ml-2 text-gray-600">{roto.justification}</span>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Stakeholders Section -->
	{#if reportData.stakeholders.length > 0}
		<section class="mb-8">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.stakeholders()} ({reportData.stakeholders.length})
			</h2>
			<div class="space-y-4">
				{#each reportData.stakeholders as stakeholder}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">
							{stakeholder.entity.str} ({safeTranslate(stakeholder.category_raw)})
						</h3>
						<div class="grid grid-cols-2 gap-4 text-sm">
							<div>
								<span class="font-semibold text-gray-700">{m.currentCriticality()}:</span>
								<span class="ml-2">{stakeholder.current_criticality}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.residualCriticality()}:</span>
								<span class="ml-2">{stakeholder.residual_criticality}</span>
							</div>
						</div>
						{#if stakeholder.applied_controls.length > 0}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.appliedControls()}:</span>
								<span class="ml-2 text-gray-600"
									>{stakeholder.applied_controls.map((c) => c.str).join(', ')}</span
								>
							</div>
						{/if}
						{#if stakeholder.justification}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.justification()}:</span>
								<span class="ml-2 text-gray-600">{stakeholder.justification}</span>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Strategic Scenarios Section -->
	{#if reportData.strategic_scenarios.length > 0}
		<section class="mb-8">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.strategicScenarios()} ({reportData.strategic_scenarios.length})
			</h2>
			<div class="space-y-4">
				{#each reportData.strategic_scenarios as scenario}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">{scenario.name}</h3>
						{#if scenario.description}
							<p class="text-gray-600 text-sm mb-3">{scenario.description}</p>
						{/if}
						<div class="flex flex-wrap gap-4 text-sm">
							<div>
								<span class="font-semibold text-gray-700">{m.gravity()}:</span>
								<span
									class="ml-2 px-2 py-1 rounded"
									style="background-color: {scenario.gravity.hexcolor}"
								>
									{safeTranslate(scenario.gravity.name)}
								</span>
							</div>
							{#if scenario.ref_id}
								<div>
									<span class="font-semibold text-gray-700">{m.refId()}:</span>
									<span class="ml-2">{scenario.ref_id}</span>
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Attack Paths Section -->
	{#if reportData.attack_paths.length > 0}
		<section class="mb-8">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.attackPaths()} ({reportData.attack_paths.length})
			</h2>
			<div class="space-y-4">
				{#each reportData.attack_paths as attackPath}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">{attackPath.name}</h3>
						{#if attackPath.description}
							<p class="text-gray-600 text-sm mb-3">{attackPath.description}</p>
						{/if}
						<div class="flex flex-wrap gap-4 text-sm">
							<div>
								<span class="font-semibold text-gray-700">{m.riskOrigin()}:</span>
								<span class="ml-2">{safeTranslate(attackPath.risk_origin)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.targetObjective()}:</span>
								<span class="ml-2">{attackPath.target_objective}</span>
							</div>
							{#if attackPath.ref_id}
								<div>
									<span class="font-semibold text-gray-700">{m.refId()}:</span>
									<span class="ml-2">{attackPath.ref_id}</span>
								</div>
							{/if}
						</div>
						{#if attackPath.stakeholders.length > 0}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.stakeholders()}:</span>
								<span class="ml-2 text-gray-600">
									{attackPath.stakeholders
										.map((s) => {
											const stakeholderData = reportData.stakeholders.find((st) => st.id === s.id);
											return stakeholderData
												? `${stakeholderData.entity.str} (${safeTranslate(stakeholderData.category_raw)})`
												: s.str;
										})
										.join(', ')}
								</span>
							</div>
						{/if}
						{#if attackPath.justification}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.justification()}:</span>
								<span class="ml-2 text-gray-600">{attackPath.justification}</span>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Operational Scenarios Section -->
	{#if reportData.operational_scenarios.length > 0}
		<section class="mb-8">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.operationalScenarios()} ({reportData.operational_scenarios.length})
			</h2>
			<div class="space-y-4">
				{#each reportData.operational_scenarios as opScenario}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">
							{opScenario.attack_path.name}
						</h3>
						{#if opScenario.attack_path.description}
							<p class="text-gray-600 text-sm mb-3">{opScenario.attack_path.description}</p>
						{/if}
						{#if opScenario.operating_modes_description}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.operatingModesDescription()}:</span>
								<p class="ml-2 text-gray-600 mt-1">{opScenario.operating_modes_description}</p>
							</div>
						{/if}
						<div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm mt-3">
							<div>
								<span class="font-semibold text-gray-700">{m.likelihood()}:</span>
								<span
									class="ml-2 px-2 py-1 rounded"
									style="background-color: {opScenario.likelihood.hexcolor}"
								>
									{safeTranslate(opScenario.likelihood.name)}
								</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.gravity()}:</span>
								<span
									class="ml-2 px-2 py-1 rounded"
									style="background-color: {opScenario.gravity.hexcolor}"
								>
									{safeTranslate(opScenario.gravity.name)}
								</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.riskLevel()}:</span>
								<span
									class="ml-2 px-2 py-1 rounded"
									style="background-color: {opScenario.risk_level.hexcolor || '#f9fafb'}"
								>
									{safeTranslate(opScenario.risk_level.name)}
								</span>
							</div>
						</div>
						{#if opScenario.threats.length > 0}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.threats()}:</span>
								<span class="ml-2 text-gray-600"
									>{opScenario.threats.map((t) => t.str).join(', ')}</span
								>
							</div>
						{/if}
						{#if opScenario.stakeholders.length > 0}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.stakeholders()}:</span>
								<span class="ml-2 text-gray-600">
									{opScenario.stakeholders
										.map((s) => {
											const stakeholderData = reportData.stakeholders.find((st) => st.id === s.id);
											return stakeholderData
												? `${stakeholderData.entity.str} (${safeTranslate(stakeholderData.category_raw)})`
												: s.str;
										})
										.join(', ')}
								</span>
							</div>
						{/if}
						{#if opScenario.justification}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.justification()}:</span>
								<span class="ml-2 text-gray-600">{opScenario.justification}</span>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}
</div>

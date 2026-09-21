<script lang="ts">
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import AssessmentIssues from '$lib/components/XRays/AssessmentIssues.svelte';
	import {
		SEVERITIES,
		aggregateQualityChecks,
		hasVisibleIssues,
		type SeverityKey
	} from '$lib/components/XRays/utils';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let tabStates = $state<Record<string, string>>({});
	let activeSeverities = $state<Record<SeverityKey, boolean>>({
		errors: true,
		warnings: true,
		info: true
	});

	const processFoldersData = (rawData: any): any[] => {
		if (!rawData || typeof rawData !== 'object') {
			return [];
		}
		return Object.entries(rawData).map(([key, value]) => {
			const valueObj = value as Record<string, any>;
			return {
				id: key,
				...valueObj,
				compliance_assessments: {
					...valueObj.compliance_assessments,
					...aggregateQualityChecks(valueObj.compliance_assessments)
				},
				risk_assessments: {
					...valueObj.risk_assessments,
					...aggregateQualityChecks(valueObj.risk_assessments)
				}
			};
		});
	};

	const countBySeverity = (folders: any[], key: SeverityKey) =>
		folders.reduce(
			(acc, folder) =>
				acc + folder.compliance_assessments[key].length + folder.risk_assessments[key].length,
			0
		);
</script>

<div class="flex flex-col space-y-4">
	<div class="card bg-surface-50-950 p-6 shadow-md rounded-lg flex flex-col space-y-4">
		{#await data.stream.data}
			<div class="flex flex-col items-center justify-center py-8">
				<div class="text-sm text-surface-600-400 mb-4">{m.xRaysLoadingData()}</div>
				<LoadingSpinner />
			</div>
		{:then rawData}
			{@const folders = processFoldersData(rawData)}
			{#if folders.length == 0}
				<div class="flex flex-col items-center justify-center py-10 space-y-3">
					<i class="fa-solid fa-circle-check text-4xl text-success-500"></i>
					<p class="text-lg text-surface-600-400">{m.xRaysEmptyMessage()}</p>
				</div>
			{:else}
				<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
					<div class="flex flex-wrap items-center gap-2">
						{#each SEVERITIES as severity (severity.key)}
							<button
								type="button"
								aria-pressed={activeSeverities[severity.key]}
								class="chip gap-2 px-3 py-1.5 rounded-base {activeSeverities[severity.key]
									? severity.preset
									: 'preset-outlined-surface-500 opacity-60'}"
								onclick={() => (activeSeverities[severity.key] = !activeSeverities[severity.key])}
							>
								<i class="fa-solid {severity.icon}"></i>
								<span class="font-bold">{countBySeverity(folders, severity.key)}</span>
								<span class="text-sm">{severity.label()}</span>
							</button>
						{/each}
					</div>
					<div class="ml-auto hidden lg:flex items-center gap-2 text-xs text-surface-600-400">
						<span
							class="size-8 shrink-0 rounded-lg bg-primary-500/10 text-primary-600-400 flex items-center justify-center"
						>
							<i class="fa-solid fa-magnifying-glass-chart"></i>
						</span>
						<p>{m.xRaysDescription()}</p>
					</div>
				</div>
			{/if}
			{#each folders as folder (folder.id)}
				{@const compliance_assessments = Object.values(
					folder.compliance_assessments.objects
				) as any[]}
				{@const risk_assessments = Object.values(folder.risk_assessments.objects) as any[]}
				<div class="border border-surface-200-800 rounded-lg bg-surface-100-900/30">
					<div class="flex items-center gap-3 px-5 py-3 border-b border-surface-200-800">
						<i class="fa-solid fa-folder-open text-primary-500"></i>
						<Anchor
							class="text-lg font-bold hover:underline text-primary-600-400"
							href="/folders/{folder.folder.id}"
						>
							{folder.folder.name}
						</Anchor>
						<div class="ml-auto flex items-center gap-1.5">
							{#each SEVERITIES as severity (severity.key)}
								{@const count =
									folder.compliance_assessments[severity.key].length +
									folder.risk_assessments[severity.key].length}
								{#if count > 0}
									<span class="badge {severity.preset} text-xs">
										<i class="fa-solid {severity.icon}"></i>
										{count}
									</span>
								{/if}
							{/each}
						</div>
					</div>
					<div class="px-5 py-3">
						<Tabs
							value={tabStates[folder.id] || 'compliance_assessments'}
							onValueChange={(e) => {
								tabStates[folder.id] = e.value;
							}}
						>
							<Tabs.List>
								{#each [{ value: 'compliance_assessments', label: m.complianceAssessments() }, { value: 'risk_assessments', label: m.riskAssessments() }] as tab (tab.value)}
									<Tabs.Trigger value={tab.value} class="inert px-2">
										{tab.label}
										{#each SEVERITIES as severity (severity.key)}
											{#if folder[tab.value][severity.key].length > 0}
												<span class="badge {severity.preset}">
													<i class="fa-solid {severity.icon}"></i>
													{folder[tab.value][severity.key].length}
												</span>
											{/if}
										{/each}
									</Tabs.Trigger>
								{/each}
								<Tabs.Indicator />
							</Tabs.List>
							{#each [{ value: 'compliance_assessments', assessments: compliance_assessments, type: 'compliance-assessments' }, { value: 'risk_assessments', assessments: risk_assessments, type: 'risk-assessments' }] as tab (tab.value)}
								<Tabs.Content value={tab.value}>
									{@const visible = tab.assessments.filter((assessment: any) =>
										hasVisibleIssues(assessment, activeSeverities)
									)}
									{#if visible.length === 0}
										<p class="text-sm text-surface-600-400 py-4">{m.xRaysNoIssues()}</p>
									{:else}
										<div class="space-y-3 py-2">
											{#each visible as assessment (assessment.object.id)}
												<AssessmentIssues
													{assessment}
													assessmentType={tab.type}
													{activeSeverities}
												/>
											{/each}
										</div>
									{/if}
								</Tabs.Content>
							{/each}
						</Tabs>
					</div>
				</div>
			{/each}
		{:catch error}
			<div class="flex flex-col items-center justify-center py-8 space-y-2">
				<i class="fa-solid fa-triangle-exclamation text-3xl text-error-500"></i>
				<p class="text-error-500 font-semibold">{m.xRaysLoadingError()}</p>
				{#if error?.message}
					<p class="text-sm text-surface-600-400">{error.message}</p>
				{/if}
			</div>
		{/await}
	</div>
</div>

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
	let openDomains = $state<Record<string, boolean>>({});
	let domainSearch = $state('');
	let sortBy = $state<'severity' | 'name'>('severity');
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

	const folderCount = (folder: any, key: SeverityKey) =>
		folder.compliance_assessments[key].length + folder.risk_assessments[key].length;

	const countBySeverity = (folders: any[], key: SeverityKey) =>
		folders.reduce((acc, folder) => acc + folderCount(folder, key), 0);

	// Errors outrank any number of warnings, warnings outrank any number of info.
	const severityWeight = (folder: any) =>
		(activeSeverities.errors ? folderCount(folder, 'errors') * 1e8 : 0) +
		(activeSeverities.warnings ? folderCount(folder, 'warnings') * 1e4 : 0) +
		(activeSeverities.info ? folderCount(folder, 'info') : 0);

	const visibleFolders = (folders: any[]) => {
		const needle = domainSearch.trim().toLowerCase();
		const kept = folders.filter(
			(folder) =>
				severityWeight(folder) > 0 &&
				(needle === '' || folder.folder.name.toLowerCase().includes(needle))
		);
		return kept.sort((a, b) =>
			sortBy === 'name'
				? a.folder.name.localeCompare(b.folder.name)
				: severityWeight(b) - severityWeight(a)
		);
	};

	const allOpen = (folders: any[]) =>
		folders.length > 0 && folders.every((folder) => openDomains[folder.id]);

	const setAllOpen = (folders: any[], open: boolean) => {
		openDomains = Object.fromEntries(folders.map((folder) => [folder.id, open]));
	};
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
			{@const shown = visibleFolders(folders)}
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
								title={m.xRaysToggleSeverity({ severity: severity.label() })}
								class="chip gap-2 px-3 py-1.5 rounded-base cursor-pointer select-none border border-surface-300-700 transition-all hover:ring-2 hover:ring-surface-400-600 {activeSeverities[
									severity.key
								]
									? severity.preset
									: 'text-surface-600-400 opacity-60'}"
								onclick={() => (activeSeverities[severity.key] = !activeSeverities[severity.key])}
							>
								<i
									class="fa-solid {activeSeverities[severity.key] ? severity.icon : 'fa-eye-slash'}"
								></i>
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

				<div class="flex flex-wrap items-center gap-2 border-y border-surface-200-800 py-2 text-sm">
					<input
						class="input bg-surface-50-950 max-w-xs text-sm"
						type="search"
						placeholder={m.searchPlaceholder()}
						aria-label={m.domains()}
						bind:value={domainSearch}
					/>
					<select
						class="select bg-surface-50-950 w-auto text-sm cursor-pointer"
						bind:value={sortBy}
					>
						<option value="severity">{m.xRaysSortBySeverity()}</option>
						<option value="name">{m.xRaysSortByName()}</option>
					</select>
					<span class="text-xs text-surface-600-400">
						{shown.length}
						{m.domains().toLowerCase()}
					</span>
					<button
						type="button"
						class="btn btn-sm preset-tonal-surface text-xs cursor-pointer ml-auto"
						title={allOpen(shown) ? m.collapseAll() : m.expandAll()}
						onclick={() => setAllOpen(shown, !allOpen(shown))}
					>
						<i class="fa-solid {allOpen(shown) ? 'fa-compress' : 'fa-expand'} mr-2"></i>
						{allOpen(shown) ? m.collapseAll() : m.expandAll()}
					</button>
				</div>
			{/if}

			{#if folders.length > 0 && shown.length === 0}
				<p class="text-sm text-surface-600-400 py-4">{m.noResults()}</p>
			{/if}

			{#each shown as folder (folder.id)}
				<details
					class="group/domain border border-surface-200-800 rounded-lg overflow-hidden"
					open={openDomains[folder.id] ?? false}
					ontoggle={(e) => (openDomains[folder.id] = e.currentTarget.open)}
				>
					<summary
						class="flex items-center gap-3 px-5 py-3 cursor-pointer list-none bg-surface-100-900/40 hover:bg-surface-100-900 transition-colors"
					>
						<i
							class="fa-solid fa-chevron-right text-xs text-surface-500 transition-transform group-open/domain:rotate-90"
						></i>
						<i class="fa-solid fa-folder-open text-secondary-500"></i>
						<span class="font-bold truncate text-secondary-950-50">{folder.folder.name}</span>
						<Anchor
							href="/folders/{folder.folder.id}"
							label={folder.folder.name}
							stopPropagation
							class="anchor underline underline-offset-2 text-xs shrink-0 whitespace-nowrap"
						>
							<i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
							{m.xRaysView()}
						</Anchor>
						<div class="ml-auto flex items-center gap-1.5 shrink-0">
							{#each SEVERITIES as severity (severity.key)}
								{@const count = folderCount(folder, severity.key)}
								{#if count > 0 && activeSeverities[severity.key]}
									<span class="badge {severity.preset} text-xs">
										<i class="fa-solid {severity.icon}"></i>
										{count}
									</span>
								{/if}
							{/each}
						</div>
					</summary>

					<!-- Rendered on open only: mounting every domain's tabs up front does not
					     scale to workspaces with hundreds of domains. -->
					{#if openDomains[folder.id]}
						{@const compliance_assessments = Object.values(
							folder.compliance_assessments.objects
						) as any[]}
						{@const risk_assessments = Object.values(folder.risk_assessments.objects) as any[]}
						<div class="px-5 py-3 bg-surface-50-950">
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
												{#if folder[tab.value][severity.key].length > 0 && activeSeverities[severity.key]}
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
					{/if}
				</details>
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

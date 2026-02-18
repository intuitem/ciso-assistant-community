<script lang="ts">
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const aggregateQualityChecks = (item: any) => {
		const types = ['errors', 'warnings', 'info'];
		const result = {};

		if (!item?.objects || typeof item.objects !== 'object') {
			types.forEach((type) => {
				result[type] = [];
			});
			return result;
		}

		types.forEach((type) => {
			result[type] = Object.entries(item.objects).reduce((acc, [key, value]) => {
				if (key !== 'object' && value?.quality_check?.[type]) {
					// if key === 'quality_check'
					acc = [...acc, ...value.quality_check[type]];
				}
				return acc;
			}, []);
		});

		return result;
	};

	const aggregateIssuesByType = (
		issues: any[] | undefined,
		assessmentType: string,
		assessmentId: string
	) => {
		if (!Array.isArray(issues) || issues.length === 0) {
			return [];
		}

		const grouped = new Map();

		issues.forEach((issue) => {
			if (!issue?.msgid || !issue?.object) {
				return; // Skip malformed issues
			}

			const key = issue.msgid;
			if (!grouped.has(key)) {
				grouped.set(key, {
					msgid: key,
					findings: []
				});
			}

			// If issue has a link, use it with /edit, otherwise link to the assessment
			const link = issue.link ? `/${issue.link}/edit` : `/${assessmentType}/${assessmentId}`;

			grouped.get(key).findings.push({
				name: issue.object.name || '',
				link: link
			});
		});

		return Array.from(grouped.values());
	};

	let tabStates = $state({});

	const processFoldersData = (rawData: any) => {
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
</script>

<div class="card bg-surface-50-950 p-6 shadow-md rounded-lg flex flex-col space-y-6">
	{#await data.stream.data}
		<div class="flex flex-col items-center justify-center py-8">
			<div class="text-sm text-surface-600-400 mb-4">{m.xRaysLoadingData()}</div>
			<LoadingSpinner />
		</div>
	{:then rawData}
		{@const folders = processFoldersData(rawData)}
		{#if folders.length == 0}
			<span class="text-2xl">{m.xRaysEmptyMessage()}</span>
		{/if}
		{#each folders as folder, index}
			{@const compliance_assessments = Object.values(folder.compliance_assessments.objects)}
			{@const risk_assessments = Object.values(folder.risk_assessments.objects)}
			<div
				class="border border-surface-200-800 rounded-lg p-6 bg-surface-50-950/50 hover:shadow-md transition-shadow"
			>
				<div class="flex items-center gap-3 mb-4">
					<span class="text-3xl">💡</span>
					<Anchor
						class="text-2xl font-bold hover:underline text-blue-600 hover:text-blue-700 transition-colors"
						href="/folders/{folder.folder.id}"
					>
						{folder.folder.name}
					</Anchor>
				</div>
				<Tabs
					value={tabStates[folder.id] || 'compliance_assessments'}
					onValueChange={(e) => {
						if (!tabStates[folder.id]) {
							tabStates[folder.id] = 'compliance_assessments';
						}
						tabStates[folder.id] = e.value;
					}}
					listJustify="justify-center"
				>
					{#snippet list()}
						<Tabs.Control value="compliance_assessments" labelBase="inert px-2"
							>{m.complianceAssessments()}
							{#if folder.compliance_assessments.errors.length > 0}
								<span class="badge preset-tonal-error"
									>{folder.compliance_assessments.errors.length}</span
								>
							{/if}
							{#if folder.compliance_assessments.warnings.length > 0}
								<span class="badge preset-tonal-warning"
									>{folder.compliance_assessments.warnings.length}</span
								>
							{/if}
							{#if folder.compliance_assessments.info.length > 0}
								<span class="badge preset-tonal-secondary"
									>{folder.compliance_assessments.info.length}</span
								>
							{/if}
						</Tabs.Control>
						<Tabs.Control value="risk_assessments" labelBase="inert px-2"
							>{m.riskAssessments()}
							{#if folder.risk_assessments.errors.length > 0}
								<span class="badge preset-tonal-error">{folder.risk_assessments.errors.length}</span
								>
							{/if}
							{#if folder.risk_assessments.warnings.length > 0}
								<span class="badge preset-tonal-warning"
									>{folder.risk_assessments.warnings.length}</span
								>
							{/if}
							{#if folder.risk_assessments.info.length > 0}
								<span class="badge preset-tonal-secondary"
									>{folder.risk_assessments.info.length}</span
								>
							{/if}
						</Tabs.Control>
					{/snippet}
					{#snippet content()}
						<Tabs.Panel value="compliance_assessments">
							<ul class="list-none pl-4 text-sm space-y-2">
								{#each compliance_assessments as compliance_assessment, index}
									<li class="h4 font-semibold mb-1">
										<Anchor
											href="/compliance-assessments/{compliance_assessment.object.id}"
											class="hover:underline text-blue-600"
											>{compliance_assessment.object.name}</Anchor
										>
									</li>
									{@const quality_check = compliance_assessment.quality_check}
									{@const aggregatedErrors = aggregateIssuesByType(
										quality_check.errors,
										'compliance-assessments',
										compliance_assessment.object.id
									)}
									{@const aggregatedWarnings = aggregateIssuesByType(
										quality_check.warnings,
										'compliance-assessments',
										compliance_assessment.object.id
									)}
									{@const aggregatedInfo = aggregateIssuesByType(
										quality_check.info,
										'compliance-assessments',
										compliance_assessment.object.id
									)}
									<div class="flex flex-col space-y-3">
										{#if aggregatedErrors.length > 0}
											<div class="space-y-2">
												<div
													class="preset-tonal-error rounded-lg px-4 py-2 flex items-center gap-2"
												>
													<i class="fa-solid fa-bug text-lg"></i>
													<span class="font-bold text-lg">{aggregatedErrors.length}</span>
													<span
														>{aggregatedErrors.length === 1
															? m.xRaysIssueType()
															: m.xRaysIssueTypes()}</span
													>
													<span class="text-sm opacity-75 ml-auto">
														{quality_check.errors.length}
														{quality_check.errors.length === 1
															? m.xRaysFinding()
															: m.xRaysFindings()}
													</span>
												</div>
												<ul class="list-none pl-2 text-sm space-y-4">
													{#each aggregatedErrors as error}
														<li class="border-l-4 border-error-500 pl-4 py-2">
															<div class="font-semibold mb-2 text-base">
																{safeTranslate(error.msgid)}
															</div>
															<div class="space-y-1.5">
																{#each error.findings as finding, idx}
																	<div
																		class="flex items-center gap-2 hover:bg-surface-100-900 rounded px-2 py-1 transition-colors"
																	>
																		<span class="text-surface-400-600 text-xs font-mono min-w-[20px]"
																			>{idx + 1}.</span
																		>
																		{#if finding.name}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{finding.name}</Anchor
																			>
																		{:else}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{m.xRaysView()}</Anchor
																			>
																		{/if}
																	</div>
																{/each}
															</div>
														</li>
													{/each}
												</ul>
											</div>
										{/if}
										{#if aggregatedWarnings.length > 0}
											<div class="space-y-2">
												<div
													class="preset-tonal-warning rounded-lg px-4 py-2 flex items-center gap-2"
												>
													<i class="fa-solid fa-triangle-exclamation text-lg"></i>
													<span class="font-bold text-lg">{aggregatedWarnings.length}</span>
													<span
														>{aggregatedWarnings.length === 1
															? m.xRaysIssueType()
															: m.xRaysIssueTypes()}</span
													>
													<span class="text-sm opacity-75 ml-auto">
														{quality_check.warnings.length}
														{quality_check.warnings.length === 1
															? m.xRaysFinding()
															: m.xRaysFindings()}
													</span>
												</div>
												<ul class="list-none pl-2 text-sm space-y-4">
													{#each aggregatedWarnings as warning}
														<li class="border-l-4 border-warning-500 pl-4 py-2">
															<div class="font-semibold mb-2 text-base">
																{safeTranslate(warning.msgid)}
															</div>
															<div class="space-y-1.5">
																{#each warning.findings as finding, idx}
																	<div
																		class="flex items-center gap-2 hover:bg-surface-100-900 rounded px-2 py-1 transition-colors"
																	>
																		<span class="text-surface-400-600 text-xs font-mono min-w-[20px]"
																			>{idx + 1}.</span
																		>
																		{#if finding.name}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{finding.name}</Anchor
																			>
																		{:else}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{m.xRaysView()}</Anchor
																			>
																		{/if}
																	</div>
																{/each}
															</div>
														</li>
													{/each}
												</ul>
											</div>
										{/if}
										{#if aggregatedInfo.length > 0}
											<div class="space-y-2">
												<div
													class="preset-tonal-secondary rounded-lg px-4 py-2 flex items-center gap-2"
												>
													<i class="fa-solid fa-circle-info text-lg"></i>
													<span class="font-bold text-lg">{aggregatedInfo.length}</span>
													<span
														>{aggregatedInfo.length === 1
															? m.xRaysIssueType()
															: m.xRaysIssueTypes()}</span
													>
													<span class="text-sm opacity-75 ml-auto">
														{quality_check.info.length}
														{quality_check.info.length === 1 ? m.xRaysFinding() : m.xRaysFindings()}
													</span>
												</div>
												<ul class="list-none pl-2 text-sm space-y-4">
													{#each aggregatedInfo as info}
														<li class="border-l-4 border-secondary-500 pl-4 py-2">
															<div class="font-semibold mb-2 text-base">
																{safeTranslate(info.msgid)}
															</div>
															<div class="space-y-1.5">
																{#each info.findings as finding, idx}
																	<div
																		class="flex items-center gap-2 hover:bg-surface-100-900 rounded px-2 py-1 transition-colors"
																	>
																		<span class="text-surface-400-600 text-xs font-mono min-w-[20px]"
																			>{idx + 1}.</span
																		>
																		{#if finding.name}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{finding.name}</Anchor
																			>
																		{:else}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{m.xRaysView()}</Anchor
																			>
																		{/if}
																	</div>
																{/each}
															</div>
														</li>
													{/each}
												</ul>
											</div>
										{/if}
									</div>
									{#if index != compliance_assessments.length - 1}
										<hr />
									{/if}
								{/each}
							</ul>
						</Tabs.Panel>
						<Tabs.Panel value="risk_assessments">
							<ul class="list-none pl-4 text-sm space-y-2">
								{#each risk_assessments as risk_assessment, index}
									<li class="h4 font-semibold mb-1">
										<Anchor
											href="/risk-assessments/{risk_assessment.object.id}"
											class="hover:underline text-blue-600">{risk_assessment.object.name}</Anchor
										>
									</li>
									{@const quality_check = risk_assessment.quality_check}
									{@const aggregatedErrors = aggregateIssuesByType(
										quality_check.errors,
										'risk-assessments',
										risk_assessment.object.id
									)}
									{@const aggregatedWarnings = aggregateIssuesByType(
										quality_check.warnings,
										'risk-assessments',
										risk_assessment.object.id
									)}
									{@const aggregatedInfo = aggregateIssuesByType(
										quality_check.info,
										'risk-assessments',
										risk_assessment.object.id
									)}
									<div class="flex flex-col space-y-3">
										{#if aggregatedErrors.length > 0}
											<div class="space-y-2">
												<div
													class="preset-tonal-error rounded-lg px-4 py-2 flex items-center gap-2"
												>
													<i class="fa-solid fa-bug text-lg"></i>
													<span class="font-bold text-lg">{aggregatedErrors.length}</span>
													<span
														>{aggregatedErrors.length === 1
															? m.xRaysIssueType()
															: m.xRaysIssueTypes()}</span
													>
													<span class="text-sm opacity-75 ml-auto">
														{quality_check.errors.length}
														{quality_check.errors.length === 1
															? m.xRaysFinding()
															: m.xRaysFindings()}
													</span>
												</div>
												<ul class="list-none pl-2 text-sm space-y-4">
													{#each aggregatedErrors as error}
														<li class="border-l-4 border-error-500 pl-4 py-2">
															<div class="font-semibold mb-2 text-base">
																{safeTranslate(error.msgid)}
															</div>
															<div class="space-y-1.5">
																{#each error.findings as finding, idx}
																	<div
																		class="flex items-center gap-2 hover:bg-surface-100-900 rounded px-2 py-1 transition-colors"
																	>
																		<span class="text-surface-400-600 text-xs font-mono min-w-[20px]"
																			>{idx + 1}.</span
																		>
																		{#if finding.name}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{finding.name}</Anchor
																			>
																		{:else}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{m.xRaysView()}</Anchor
																			>
																		{/if}
																	</div>
																{/each}
															</div>
														</li>
													{/each}
												</ul>
											</div>
										{/if}
										{#if aggregatedWarnings.length > 0}
											<div class="space-y-2">
												<div
													class="preset-tonal-warning rounded-lg px-4 py-2 flex items-center gap-2"
												>
													<i class="fa-solid fa-triangle-exclamation text-lg"></i>
													<span class="font-bold text-lg">{aggregatedWarnings.length}</span>
													<span
														>{aggregatedWarnings.length === 1
															? m.xRaysIssueType()
															: m.xRaysIssueTypes()}</span
													>
													<span class="text-sm opacity-75 ml-auto">
														{quality_check.warnings.length}
														{quality_check.warnings.length === 1
															? m.xRaysFinding()
															: m.xRaysFindings()}
													</span>
												</div>
												<ul class="list-none pl-2 text-sm space-y-4">
													{#each aggregatedWarnings as warning}
														<li class="border-l-4 border-warning-500 pl-4 py-2">
															<div class="font-semibold mb-2 text-base">
																{safeTranslate(warning.msgid)}
															</div>
															<div class="space-y-1.5">
																{#each warning.findings as finding, idx}
																	<div
																		class="flex items-center gap-2 hover:bg-surface-100-900 rounded px-2 py-1 transition-colors"
																	>
																		<span class="text-surface-400-600 text-xs font-mono min-w-[20px]"
																			>{idx + 1}.</span
																		>
																		{#if finding.name}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{finding.name}</Anchor
																			>
																		{:else}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{m.xRaysView()}</Anchor
																			>
																		{/if}
																	</div>
																{/each}
															</div>
														</li>
													{/each}
												</ul>
											</div>
										{/if}
										{#if aggregatedInfo.length > 0}
											<div class="space-y-2">
												<div
													class="preset-tonal-secondary rounded-lg px-4 py-2 flex items-center gap-2"
												>
													<i class="fa-solid fa-circle-info text-lg"></i>
													<span class="font-bold text-lg">{aggregatedInfo.length}</span>
													<span
														>{aggregatedInfo.length === 1
															? m.xRaysIssueType()
															: m.xRaysIssueTypes()}</span
													>
													<span class="text-sm opacity-75 ml-auto">
														{quality_check.info.length}
														{quality_check.info.length === 1 ? m.xRaysFinding() : m.xRaysFindings()}
													</span>
												</div>
												<ul class="list-none pl-2 text-sm space-y-4">
													{#each aggregatedInfo as info}
														<li class="border-l-4 border-secondary-500 pl-4 py-2">
															<div class="font-semibold mb-2 text-base">
																{safeTranslate(info.msgid)}
															</div>
															<div class="space-y-1.5">
																{#each info.findings as finding, idx}
																	<div
																		class="flex items-center gap-2 hover:bg-surface-100-900 rounded px-2 py-1 transition-colors"
																	>
																		<span class="text-surface-400-600 text-xs font-mono min-w-[20px]"
																			>{idx + 1}.</span
																		>
																		{#if finding.name}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{finding.name}</Anchor
																			>
																		{:else}
																			<Anchor class="anchor text-sm" href={finding.link}
																				>{m.xRaysView()}</Anchor
																			>
																		{/if}
																	</div>
																{/each}
															</div>
														</li>
													{/each}
												</ul>
											</div>
										{/if}
									</div>
									{#if index != risk_assessments.length - 1}
										<hr />
									{/if}
								{/each}
							</ul>
						</Tabs.Panel>
					{/snippet}
				</Tabs>
			</div>
			{#if index != folders.length - 1}
				<hr />
			{/if}
		{/each}
	{:catch error}
		<div class="flex flex-col items-center justify-center py-8">
			<p class="text-red-500">Error loading data</p>
		</div>
	{/await}
</div>

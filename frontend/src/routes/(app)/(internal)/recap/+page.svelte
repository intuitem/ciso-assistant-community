<script lang="ts">
	import DonutChart from '#lib/components/Chart/DonutChart.svelte';
	import { m } from '#paraglide/messages.js';
	import { page } from '$app/state';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { displayScoreColor, formatScoreValue, roundScore } from '#lib/utils/helpers.js';
	import type { PageData } from './$types';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import { canPerformAction } from '#lib/utils/access-control.js';
	import { replaceState } from '$app/navigation';
	import FrameworkReportsList from './FrameworkReportsList.svelte';
	import { safeTranslate } from '#lib/utils/i18n.js';

	const REQUIREMENT_ASSESSMENT_STATUS = [
		'compliant',
		'partially_compliant',
		'in_progress',
		'non_compliant',
		'not_applicable',
		'to_do'
	] as const;

	const user = page.data.user;
	import { URL_MODEL_MAP } from '#lib/utils/crud.js';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const foldersWithAssessments = $derived(
		data.folderRecaps.filter((folderRecap) => folderRecap.compliance_assessments.length > 0)
	);

	const TABS = ['frameworks', 'domains'] as const;
	type Tab = (typeof TABS)[number];
	let tab = $state<Tab>(page.url.searchParams.get('tab') === 'domains' ? 'domains' : 'frameworks');
	const tabLabel = { domains: () => m.byDomain(), frameworks: () => m.byFramework() };
	function selectTab(next: Tab) {
		tab = next;
		const url = new URL(page.url.href);
		if (next === 'frameworks') url.searchParams.delete('tab');
		else url.searchParams.set('tab', next);
		replaceState(url, page.state);
	}
	function onTabKeydown(event: KeyboardEvent) {
		const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
		if (!step) return;
		event.preventDefault();
		const next = TABS[(TABS.indexOf(tab) + step + TABS.length) % TABS.length];
		selectTab(next);
		document.getElementById(`recap-tab-${next}`)?.focus();
	}

	const model = URL_MODEL_MAP['folders'];
	const canEditObject = (folder): boolean =>
		canPerformAction({
			user,
			action: 'change',
			model: model.name,
			domain: folder.id
		});
</script>

<div class="p-4 space-y-6 bg-surface-50-950 min-h-screen card">
	<h2 class="text-2xl font-extrabold text-surface-950-50">{m.recap()}</h2>

	<div class="flex gap-1 border-b border-surface-200-800" role="tablist">
		{#each TABS as t}
			<button
				type="button"
				role="tab"
				id="recap-tab-{t}"
				aria-selected={tab === t}
				aria-controls="recap-panel"
				tabindex={tab === t ? 0 : -1}
				onkeydown={onTabKeydown}
				class="px-4 py-2 text-sm font-medium -mb-px border-b-2 {tab === t
					? 'border-primary-500 text-primary-700 dark:text-primary-300'
					: 'border-transparent text-surface-600-400 hover:text-surface-950-50'}"
				onclick={() => selectTab(t)}
			>
				{tabLabel[t]()}
			</button>
		{/each}
	</div>

	<div id="recap-panel" role="tabpanel" aria-labelledby="recap-tab-{tab}">
		{#if tab === 'frameworks'}
			<FrameworkReportsList frameworks={data.usedFrameworks} error={data.usedFrameworksError} />
		{:else}
			<div class="space-y-6">
				{#if foldersWithAssessments.length === 0}
					<div class="flex items-center justify-center min-h-[60vh]">
						<div class="text-center max-w-lg">
							<p class="text-xl font-bold text-surface-950-50">
								{m.createYourFirstAuditToSeeRecapPage()}
							</p>
							<p class="mt-2 text-sm text-surface-600-400">
								{m.AuditExistsYoullSeeOverallCompliance()}
							</p>
						</div>
					</div>
				{:else}
					{#each foldersWithAssessments as folder (folder.id)}
						<section class="rounded-xl border border-surface-200-800 bg-surface-50-950 shadow-sm">
							<header
								class="grid gap-3 p-4 border-b border-surface-200-800 md:grid-cols-[minmax(0,16rem)_minmax(0,1fr)] md:items-center"
							>
								<div class="flex items-center gap-2 min-w-0">
									<i class="fa-solid fa-sitemap text-primary-500" aria-hidden="true"></i>
									<a class="text-lg font-bold truncate hover:underline" href="/folders/{folder.id}">
										{folder.name}
									</a>
									<span class="badge preset-tonal-primary shrink-0">
										{m.auditsCount({ count: folder.compliance_assessments.length })}
									</span>
								</div>
								{#if folder.overallCompliance?.values?.length > 0}
									<div>
										<p class="text-xs text-surface-600-400 mb-1">{m.globalOverall()}</p>
										<div class="flex h-4 rounded-md overflow-hidden border border-surface-200-800">
											{#each folder.overallCompliance.values.toSorted((a, b) => REQUIREMENT_ASSESSMENT_STATUS.indexOf(a.name) - REQUIREMENT_ASSESSMENT_STATUS.indexOf(b.name)) as sp}
												<div
													class="flex justify-center items-center text-[10px] font-semibold"
													style="width: {sp.percentage}%; background-color: {sp.itemStyle
														.color}; color: {['#475569', '#000000'].includes(sp.itemStyle.color)
														? 'white'
														: 'black'};"
													title="{safeTranslate(sp.name)}: {sp.percentage}%"
												>
													{Number(sp.percentage) > 6 ? `${sp.percentage}%` : ''}
												</div>
											{/each}
										</div>
									</div>
								{/if}
							</header>

							<div class="grid gap-4 p-4 sm:grid-cols-2 2xl:grid-cols-3">
								{#each folder.compliance_assessments as assessment (assessment.id)}
									<article
										class="flex flex-col gap-3 rounded-lg border border-surface-200-800 p-4 transition hover:shadow-md hover:border-primary-300"
									>
										<div class="min-w-0">
											<a
												class="block font-bold text-primary-700 dark:text-primary-300 hover:underline truncate"
												href="/compliance-assessments/{assessment.id}"
												title={assessment.name}
											>
												{assessment.name}
											</a>
											<p
												class="text-xs text-surface-600-400 truncate"
												title={assessment.framework.str}
											>
												{assessment.framework.str}
											</p>
										</div>

										<div
											class="grid items-center gap-3 {assessment.global_score.maturity_score >= 0
												? 'grid-cols-[auto_minmax(0,1fr)]'
												: 'grid-cols-1'}"
										>
											{#if assessment.global_score.maturity_score >= 0}
												<div class="relative" title={m.maturity()}>
													<Progress
														value={formatScoreValue(
															assessment.global_score.maturity_score,
															assessment.global_score.max_score,
															false,
															assessment.global_score.min_score
														)}
														min={0}
														max={100}
													>
														<Progress.Circle class="[--size:--spacing(20)]">
															<Progress.CircleTrack />
															<Progress.CircleRange
																class={displayScoreColor(
																	assessment.global_score.maturity_score,
																	assessment.global_score.max_score,
																	false,
																	assessment.global_score.min_score
																)}
															/>
														</Progress.Circle>
														<div class="absolute inset-0 flex items-center justify-center">
															<p class="font-semibold text-lg">
																{roundScore(assessment.global_score.maturity_score)}
															</p>
														</div>
													</Progress>
												</div>
											{/if}
											<div class="h-36">
												<DonutChart
													s_label={m.complianceAssessments()}
													name={assessment.name + '_donut'}
													values={assessment.donut.result.values}
												/>
											</div>
										</div>

										<div class="mt-auto grid grid-cols-2 gap-2">
											{#if canEditObject(folder)}
												<Anchor
													href="/compliance-assessments/{assessment.id}/edit?next=/recap?tab=domains"
													class="btn btn-sm preset-outlined-primary-500"
												>
													<i class="fa-solid fa-edit mr-1"></i>
													{m.edit()}
												</Anchor>
											{/if}
											<a
												href="/compliance-assessments/{assessment.id}/export"
												class="btn btn-sm preset-filled-primary-500 {canEditObject(folder)
													? ''
													: 'col-span-2'}"
											>
												<i class="fa-solid fa-download mr-1"></i>
												{m.exportButton()}
											</a>
										</div>
									</article>
								{/each}
							</div>
						</section>
					{/each}
				{/if}
			</div>
		{/if}
	</div>
</div>

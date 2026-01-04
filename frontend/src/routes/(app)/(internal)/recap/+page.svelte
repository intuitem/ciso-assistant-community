<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { canPerformAction } from '$lib/utils/access-control';

	const REQUIREMENT_ASSESSMENT_STATUS = [
		'compliant',
		'partially_compliant',
		'in_progress',
		'non_compliant',
		'not_applicable',
		'to_do'
	] as const;

	const user = page.data.user;
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const model = URL_MODEL_MAP['perimeters'];
	const canEditObject = (perimeter): boolean =>
		canPerformAction({
			user,
			action: 'change',
			model: model.name,
			domain: perimeter.folder?.id
		});
</script>

<div class="p-4 space-y-6 bg-gray-50 min-h-screen">
	<h2 class="text-2xl font-extrabold text-gray-800 mb-4">{m.overallCompliance()}</h2>

	<div class="space-y-6">
		{#each data.perimeters as perimeter}
			{#if perimeter.compliance_assessments.length > 0}
				<div
					class="bg-white shadow-lg rounded-xl border border-gray-200 overflow-hidden transition hover:shadow-xl transform w-full"
				>
					<div
						class="p-4 bg-gradient-to-r from-primary-400 to-primary-500 text-white flex justify-between items-center"
					>
						<a class="text-lg font-bold hover:underline" href="/perimeters/{perimeter.id}">
							{perimeter.folder.str}/{perimeter.name}
						</a>
					</div>
					{#if perimeter.overallCompliance?.values?.length > 0}
						<div class="px-4 py-3 bg-gradient-to-r from-primary-50 to-primary-100 rounded-b-lg">
							<p class="text-sm font-semibold text-primary-700 mb-2">{m.globalOverall()}</p>
							<div class="flex h-6 rounded-lg overflow-hidden shadow-inner">
								{#each perimeter.overallCompliance.values.sort((a, b) => REQUIREMENT_ASSESSMENT_STATUS.indexOf(a.name) - REQUIREMENT_ASSESSMENT_STATUS.indexOf(b.name)) as sp}
									<div
										class="flex justify-center items-center text-xs font-semibold"
										style="
						width: {sp.percentage}%;
						background-color: {sp.itemStyle.color};
						color: {sp.itemStyle.color === '#000000' ? 'white' : 'black'};
						box-shadow: inset 0 0 1px rgba(0,0,0,0.3);
					"
									>
										{Number(sp.percentage) > 5 ? `${sp.percentage}%` : ''}
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<div class="p-4 space-y-4">
						{#each perimeter.compliance_assessments as assessment}
							<div class="bg-gray-50 rounded-lg p-4 shadow-inner transition hover:bg-gray-100">
								<div class="flex justify-between items-center mb-4">
									<div>
										<p class="text-sm font-semibold">{m.name()}</p>
										<a
											class="text-blue-600 hover:underline text-lg font-bold"
											href="/compliance-assessments/{assessment.id}"
										>
											{assessment.name}
										</a>
									</div>
									<div>
										<p class="text-sm font-semibold">{m.framework()}</p>
										<p>{assessment.framework.str}</p>
									</div>
								</div>

								<div class="flex flex-col lg:flex-row items-center justify-between gap-4">
									{#if assessment.globalScore.score >= 0}
										<div class="flex justify-center items-center lg:order-1">
											<ProgressRing
												strokeWidth="16px"
												meterStroke={displayScoreColor(
													assessment.globalScore.score,
													assessment.globalScore.max_score
												)}
												value={formatScoreValue(
													assessment.globalScore.score,
													assessment.globalScore.max_score
												)}
												size="size-24"
											>
												<p class="font-semibold text-2xl">{assessment.globalScore.score}</p>
											</ProgressRing>
										</div>
									{/if}

									<div class="w-full lg:w-3/5 h-40 lg:h-32">
										<DonutChart
											s_label={m.complianceAssessments()}
											name={assessment.name + '_donut'}
											values={assessment.donut.result.values}
										/>
									</div>

									<div
										class="flex flex-row lg:flex-col space-x-2 lg:space-x-0 lg:space-y-2 lg:order-3"
									>
										{#if canEditObject(perimeter)}
											<Anchor
												href="/compliance-assessments/{assessment.id}/edit?next=/recap"
												class="btn preset-filled-primary-500 w-1/2 lg:w-full"
											>
												<i class="fa-solid fa-edit mr-2"></i>
												{m.edit()}
											</Anchor>
										{/if}
										<a
											href="/compliance-assessments/{assessment.id}/export"
											class="btn preset-filled-primary-500 w-1/2 lg:w-full"
										>
											<i class="fa-solid fa-download mr-2"></i>
											{m.exportButton()}
										</a>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		{/each}
	</div>
</div>

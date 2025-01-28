<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import * as m from '$paraglide/messages';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	export let data: PageData;

	const REQUIREMENT_ASSESSMENT_STATUS = [
		'compliant',
		'partially_compliant',
		'in_progress',
		'non_compliant',
		'not_applicable',
		'to_do'
	] as const;
</script>

<div class="px-4 pb-4 space-y-8">
	<span class="text-xl font-extrabold">{m.overallCompliance()}</span>
	<div class="flex flex-col space-y-2">
		{#each data.projects as project}
			<div class="flex flex-col items-center">
				{#if project.compliance_assessments && project.compliance_assessments.length > 0}
					<div
						class="flex flex-col lg:flex-row lg:space-x-2 w-full mb-2 lg:mb-0 lg:w-1/2 justify-between items-center"
					>
						<a
							class="text-xl font-bold mb-1 hover:underline text-primary-600"
							href="/projects/{project.id}">{project.folder.str}/{project.name}</a
						>
						<div
							class="flex w-full flex-row lg:flex-1 bg-gray-200 rounded-full overflow-hidden h-4 grow lg:shrink"
						>
							{#each project.overallCompliance.values.sort((a, b) => REQUIREMENT_ASSESSMENT_STATUS.indexOf(a.name) - REQUIREMENT_ASSESSMENT_STATUS.indexOf(b.name)) as sp}
								<div
									class="flex flex-col justify-center overflow-hidden text-black text-xs text-center"
									style="width: {sp.percentage}%; background-color: {sp.itemStyle.color}"
								>
									{sp.percentage}%
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#each project.compliance_assessments as compliance_assessment}
					<div
						class="card w-full bg-white flex flex-row mx-8 p-4 relative flex-wrap lg:flex-nowrap"
					>
						<div class="w-full lg:w-1/5 flex flex-col space-y-2">
							<div>
								<p class="text-sm font-semibold">{m.name()}</p>
								<a class="anchor" href="compliance-assessments/{compliance_assessment.id}"
									>{compliance_assessment.name}</a
								>
							</div>
							<div>
								<p class="text-sm font-semibold">{m.framework()}</p>
								<p>{compliance_assessment.framework.str}</p>
							</div>
						</div>
						{#if compliance_assessment.globalScore.score >= 0}
							<div class="justify-center flex items-center">
								<ProgressRadial
									stroke={100}
									meter={displayScoreColor(
										compliance_assessment.globalScore.score,
										compliance_assessment.globalScore.max_score
									)}
									value={formatScoreValue(
										compliance_assessment.globalScore.score,
										compliance_assessment.globalScore.max_score
									)}
									font={150}
									width={'w-20'}>{compliance_assessment.globalScore.score}</ProgressRadial
								>
							</div>
						{/if}
						<div class="w-full lg:w-3/5 h-40 lg:h-32">
							<DonutChart
								s_label={m.complianceAssessments()}
								name={compliance_assessment.name + '_donut'}
								values={compliance_assessment.donut.result.values}
							/>
						</div>
						<div class="lg:absolute lg:top-2 lg:right-4 mt-2 space-x-1">
							<div class="flex flex-row lg:flex-col space-x-1 lg:space-x-0 lg:space-y-1">
								<Anchor
									href="/compliance-assessments/{compliance_assessment.id}/edit?next=/analytics?tab=3"
									prefixCrumbs={[
										{
											label: compliance_assessment.name,
											href: `/compliance-assessments/${compliance_assessment.id}`
										}
									]}
									class="btn variant-filled-primary w-1/2 lg:w-full"
									><i class="fa-solid fa-edit mr-2" /> {m.edit()}
								</Anchor>
								<a
									href="/compliance-assessments/{compliance_assessment.id}/export"
									class="btn variant-filled-primary w-1/2 lg:w-full"
									><i class="fa-solid fa-download mr-2" /> {m.exportButton()}
								</a>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/each}
	</div>
</div>

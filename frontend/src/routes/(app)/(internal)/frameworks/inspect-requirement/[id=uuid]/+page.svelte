<script lang="ts">
	import type { PageData } from './$types';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';
	import { safeTranslate } from '$lib/utils/i18n';
	import { darkenColor } from '$lib/utils/helpers';
	import { page } from '$app/stores';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';

	export let data: PageData;

	function findRequirementAssessment(audit: string, requirementAssessments: any[]): any {
		return requirementAssessments.find((ra) => ra.compliance_assessment.id === audit);
	}

	// Initialize the currentIndex for each perimeter
	$: metricsData = data.metrics.map((domain) => {
		return {
			...domain,
			perimeters: domain.perimeters.map((perimeter) => {
				return {
					...perimeter,
					currentIndex: 0
				};
			})
		};
	});

	function updateCurrentIndex(domainIndex: number, perimeterIndex: number, increment: number) {
		const domain = metricsData[domainIndex];
		const perimeter = domain.perimeters[perimeterIndex];
		const newIndex =
			(perimeter.currentIndex + increment + perimeter.compliance_assessments.length) %
			perimeter.compliance_assessments.length;

		const updatedPerimeter = { ...perimeter, currentIndex: newIndex };

		const updatedPerimeters = [...domain.perimeters];
		updatedPerimeters[perimeterIndex] = updatedPerimeter;

		const updatedDomain = { ...domain, perimeters: updatedPerimeters };

		metricsData = [...metricsData];
		metricsData[domainIndex] = updatedDomain;
	}
</script>

<div
	class="card px-6 py-4 bg-white flex flex-col justify-center items-center shadow-lg w-full rounded-lg"
>
	{#if data.requirementAssessments.length > 0}
		<span class="text-2xl font-bold text-gray-800">{data.requirementAssessments[0].name}</span>
		<span class="text-sm text-center text-gray-600"
			>{data.requirementAssessments[0].description}</span
		>
		{#each metricsData as domain, domainIndex}
			<Accordion>
				<AccordionItem open>
					<svelte:fragment slot="lead"
						><i class="fa-solid fa-sitemap text-primary-500"></i></svelte:fragment
					>
					<svelte:fragment slot="summary"
						><div class="flex flex-row space-x-4 items-center">
							<span class="font-bold text-lg text-gray-800">{domain.name}</span>
							<div>
								<div class="flex items-center space-x-2 text-sm">
									<p class="text-gray-600">Compliant Requirements:</p>
									<span class="font-bold text-green-500"
										>{domain.compliance_result.compliance_percentage}%</span
									>
									<span class="text-sm ml-2 text-gray-600"
										>({domain.compliance_result.compliant_count} / {domain.compliance_result
											.total_count})</span
									>
								</div>
								<div class="h-2 bg-gray-200 rounded-full mt-2">
									<div
										class="h-full bg-green-500 rounded-full"
										style="width: {domain.compliance_result.compliance_percentage}%;"
									></div>
								</div>
							</div>
							<div>
								<div class="flex items-center space-x-2 text-sm">
									<p class="text-gray-600">Requirements Progression:</p>
									<span class="font-bold text-blue-500"
										>{domain.assessment_progress.assessment_completion_rate}%</span
									>
									<span class="text-sm ml-2 text-gray-600"
										>({domain.assessment_progress.assessed_count} / {domain.assessment_progress
											.total_count})</span
									>
								</div>
								<div class="h-2 bg-gray-200 rounded-full mt-2">
									<div
										class="h-full bg-blue-500 rounded-full"
										style="width: {domain.assessment_progress.assessment_completion_rate}%;"
									></div>
								</div>
							</div>
						</div></svelte:fragment
					>
					<svelte:fragment slot="content">
						<div class="grid grid-cols-3 gap-4">
							{#each domain.perimeters as perimeter, perimeterIndex}
								{@const assessment = perimeter.compliance_assessments[perimeter.currentIndex]}
								{@const requirementAssessment = findRequirementAssessment(
									assessment.id,
									data.requirementAssessments
								)}
								<div class="flex flex-col p-4 bg-gray-100 shadow-md rounded-lg space-y-2">
									<span class="font-bold text-lg text-gray-800"
										><i class="fa-solid fa-cubes mr-2 text-primary-500"></i> {perimeter.name}</span
									>
									<div class="flex flex-col items-center space-y-2 h-full">
										{#if perimeter.compliance_assessments.length > 1}
											<div class="flex w-full items-center justify-between space-x-4">
												<button
													class="px-4 bg-gray-200 rounded"
													on:click={() => updateCurrentIndex(domainIndex, perimeterIndex, -1)}
												>
													<i class="fa-solid fa-arrow-left"></i>
												</button>
												<Anchor
													breadcrumbAction="push"
													href={`/compliance-assessments/${assessment.id}?next=${$page.url.pathname}`}
													label={assessment.name}
													class="font-bold text-lg text-primary-500 whitespace-nowrap text-ellipsis overflow-hidden"
												>
													<i class="fa-solid fa-certificate mr-2 text-gray-800"></i>
													{assessment.name} - {assessment.version}
												</Anchor>
												<button
													class="px-4 bg-gray-200 rounded"
													on:click={() => updateCurrentIndex(domainIndex, perimeterIndex, 1)}
												>
													<i class="fa-solid fa-arrow-right"></i>
												</button>
											</div>
										{:else}
											<div class="flex w-full items-center justify-center">
												<Anchor
													breadcrumbAction="push"
													href={`/compliance-assessments/${assessment.id}?next=${$page.url.pathname}`}
													label={assessment.name}
													class="font-bold text-lg text-primary-500 whitespace-nowrap text-ellipsis overflow-hidden"
												>
													<i class="fa-solid fa-certificate mr-2 text-gray-800"></i>
													{assessment.name} - {assessment.version}
												</Anchor>
											</div>
										{/if}
										<Anchor
											breadcrumbAction="push"
											href={`/requirement-assessments/${requirementAssessment.id}?next=${$page.url.pathname}`}
											label={requirementAssessment.name}
											class="flex flex-col items-center justify-center space-y-2 border w-full h-full p-2 rounded-lg bg-gray-200 shadow-md hover:border-2"
											style="border-color: {complianceResultColorMap[requirementAssessment.result]};
											background-color: {complianceResultColorMap[requirementAssessment.result] + '10'};"
										>
											<div class="flex flex-row space-x-2">
												<span
													class="badge h-fit whitespace-nowrap w-fit"
													style="background-color: {complianceStatusColorMap[
														requirementAssessment.status
													] + '44'}; color: {darkenColor(
														complianceStatusColorMap[requirementAssessment.status],
														0.3
													)};"
												>
													{safeTranslate(requirementAssessment.status)}
												</span>
												<span
													class="badge h-fit whitespace-nowrap w-fit"
													style="background-color: {complianceResultColorMap[
														requirementAssessment.result
													] + '44'}; color: {darkenColor(
														complianceResultColorMap[requirementAssessment.result],
														0.3
													)};"
												>
													{safeTranslate(requirementAssessment.result)}
												</span>
											</div>
											{#if requirementAssessment.is_scored}
												<div class="flex flex-row space-x-2">
													<ProgressRadial
														stroke={100}
														meter={displayScoreColor(
															requirementAssessment.score,
															assessment.max_score
														)}
														value={formatScoreValue(
															requirementAssessment.score,
															assessment.max_score
														)}
														font={150}
														class="shrink-0"
														width={'w-10'}>{requirementAssessment.score}</ProgressRadial
													>
													{#if assessment.show_documentation_score}
														<ProgressRadial
															stroke={100}
															meter={displayScoreColor(
																requirementAssessment.documentation_score,
																assessment.max_score
															)}
															value={formatScoreValue(
																requirementAssessment.documentation_score,
																assessment.max_score
															)}
															font={150}
															class="shrink-0"
															width={'w-10'}
															>{requirementAssessment.documentation_score}</ProgressRadial
														>
													{/if}
												</div>
											{/if}
										</Anchor>
									</div>
								</div>
							{/each}
						</div>
					</svelte:fragment>
				</AccordionItem>
			</Accordion>
		{/each}
	{:else}
		<div class="flex flex-col items-center justify-center h-full">
			<div class="text-center">
				<h1 class="text-2xl font-bold">No requirements found</h1>
				<p class="text-gray-500">There is no audit for this framework.</p>
			</div>
		</div>
	{/if}
</div>

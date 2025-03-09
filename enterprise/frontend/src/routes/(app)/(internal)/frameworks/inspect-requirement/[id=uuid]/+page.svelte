<script lang="ts">
	import type { PageData } from './$types';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';
	import { safeTranslate } from '$lib/utils/i18n';
	import * as m from '$paraglide/messages';
	import { darkenColor } from '$lib/utils/helpers';
	import { page } from '$app/stores';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';

	export let data: PageData;

	// Create a map for faster lookups
	$: memoizedRequirementAssessments = new Map(
		data.requirementAssessments.map((ra) => [ra.compliance_assessment.id, ra])
	);

	function findRequirementAssessment(audit: string): any {
		return memoizedRequirementAssessments.get(audit);
	}

	// Store only the current indices instead of duplicating the entire data structure
	$: currentIndices = data.metrics.map((domain) => domain.perimeters.map(() => 0));

	function updateCurrentIndex(domainIndex: number, perimeterIndex: number, increment: number) {
		const perimeter = data.metrics[domainIndex].perimeters[perimeterIndex];
		const newIndex =
			(currentIndices[domainIndex][perimeterIndex] +
				increment +
				perimeter.compliance_assessments.length) %
			perimeter.compliance_assessments.length;

		// Update only the specific index that changed
		currentIndices[domainIndex][perimeterIndex] = newIndex;
		currentIndices = [...currentIndices]; // Trigger reactivity
	}

	function hasMultipleAssessments(perimeter: any) {
		return perimeter.compliance_assessments.length > 1;
	}

	// Style helpers
	function getBadgeStyle(color: string) {
		return `background-color: ${color + '44'}; color: ${darkenColor(color, 0.3)};`;
	}
</script>

<div
	class="card px-6 py-4 bg-white flex flex-col justify-center items-center shadow-lg w-full rounded-lg"
>
	{#if data.requirementAssessments.length > 0}
		{@const firstAssessment = data.requirementAssessments[0]}
		<div class="flex flex-col text-center pt-2 pb-4">
			{#if firstAssessment?.name}
				<span class="text-2xl font-black text-gray-800">{firstAssessment.name}</span>
			{/if}
			{#if firstAssessment?.description}
				<span class="text-gray-600 blockquote">{firstAssessment.description}</span>
			{/if}
		</div>

		{#each data.metrics as domain, domainIndex}
			<Accordion class="my-4">
				<AccordionItem open>
					<svelte:fragment slot="lead">
						<i class="fa-solid fa-sitemap text-primary-500"></i>
					</svelte:fragment>

					<svelte:fragment slot="summary">
						<div class="flex flex-row space-x-4 items-center">
							<span class="font-bold text-lg text-gray-800">{domain.name}</span>

							<!-- Compliance section -->
							<div>
								<div class="flex items-center space-x-2 text-sm">
									<p class="text-gray-600">{m.compliantRequirementsSemiColon()}</p>
									<span class="font-bold text-green-500">
										{domain.compliance_result.compliance_percentage}%
									</span>
									<span class="text-sm ml-2 text-gray-600">
										({domain.compliance_result.compliant_count} / {domain.compliance_result
											.total_count})
									</span>
								</div>
								<div class="h-2 bg-gray-200 rounded-full mt-2">
									<div
										class="h-full bg-green-500 rounded-full"
										style="width: {domain.compliance_result.compliance_percentage}%;"
									></div>
								</div>
							</div>

							<!-- Progress section -->
							<div>
								<div class="flex items-center space-x-2 text-sm">
									<p class="text-gray-600">{m.requirementsProgressionSemiColon()}</p>
									<span class="font-bold text-blue-500">
										{domain.assessment_progress.assessment_completion_rate}%
									</span>
									<span class="text-sm ml-2 text-gray-600">
										({domain.assessment_progress.assessed_count} / {domain.assessment_progress
											.total_count})
									</span>
								</div>
								<div class="h-2 bg-gray-200 rounded-full mt-2">
									<div
										class="h-full bg-blue-500 rounded-full"
										style="width: {domain.assessment_progress.assessment_completion_rate}%;"
									></div>
								</div>
							</div>
						</div>
					</svelte:fragment>

					<svelte:fragment slot="content">
						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
							{#each domain.perimeters as perimeter, perimeterIndex}
								{@const assessment =
									perimeter.compliance_assessments[currentIndices[domainIndex][perimeterIndex]]}
								{@const requirementAssessment = findRequirementAssessment(assessment.id)}

								{#if requirementAssessment}
									<div class="flex flex-col p-4 bg-gray-100 shadow-md rounded-lg space-y-2">
										<span class="font-bold text-lg text-gray-800">
											<i class="fa-solid fa-cubes mr-2 text-primary-500"></i>
											{perimeter.name}
										</span>

										<div class="flex flex-col items-center space-y-2 h-full">
											{#if hasMultipleAssessments(perimeter)}
												<div class="flex w-full items-center justify-between space-x-4">
													<button
														aria-label="Previous assessment"
														class="px-4 bg-gray-200 rounded hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
														on:click={() => updateCurrentIndex(domainIndex, perimeterIndex, -1)}
													>
														<i class="fa-solid fa-arrow-left"></i>
													</button>

													<Anchor
														breadcrumbAction="push"
														href={`/compliance-assessments/${assessment.id}?next=${$page.url.pathname}`}
														label={assessment.name}
														class="font-semibold text-lg text-primary-500 whitespace-nowrap text-ellipsis overflow-hidden"
													>
														<i class="fa-solid fa-list-check mr-2 text-gray-800"></i>
														{assessment.name} - {assessment.version}
													</Anchor>

													<button
														aria-label="Next assessment"
														class="px-4 bg-gray-200 rounded hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
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
														class="font-semibold text-lg text-primary-500 whitespace-nowrap text-ellipsis overflow-hidden"
													>
														<i class="fa-solid fa-list-check mr-2 text-gray-800"></i>
														{assessment.name} - {assessment.version}
													</Anchor>
												</div>
											{/if}

											<!-- Requirement Assessment Card -->
											<Anchor
												breadcrumbAction="push"
												href={`/requirement-assessments/${requirementAssessment.id}?next=${$page.url.pathname}`}
												label={requirementAssessment.name}
												class="flex flex-col items-center justify-center space-y-2 border w-full h-full p-2 rounded-lg bg-gray-200 shadow-md hover:border-2"
												style="border-color: {complianceResultColorMap[
													requirementAssessment.result
												]};
												background-color: {complianceResultColorMap[requirementAssessment.result] + '10'};"
											>
												<div class="flex flex-row space-x-2">
													<span
														class="badge h-fit whitespace-nowrap w-fit"
														style={getBadgeStyle(
															complianceStatusColorMap[requirementAssessment.status]
														)}
													>
														{safeTranslate(requirementAssessment.status)}
													</span>
													<span
														class="badge h-fit whitespace-nowrap w-fit"
														style={getBadgeStyle(
															complianceResultColorMap[requirementAssessment.result]
														)}
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
															width={'w-10'}
														>
															{requirementAssessment.score}
														</ProgressRadial>

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
															>
																{requirementAssessment.documentation_score}
															</ProgressRadial>
														{/if}
													</div>
												{/if}
											</Anchor>
										</div>
									</div>
								{/if}
							{/each}
						</div>
					</svelte:fragment>
				</AccordionItem>
			</Accordion>
		{/each}
	{:else}
		<div class="flex flex-col items-center justify-center h-full">
			<div class="text-center">
				<h1 class="text-2xl font-bold">{m.noRequirementFound()}</h1>
				<p class="text-gray-500">{m.noAuditForTheFramework()}</p>
			</div>
		</div>
	{/if}
</div>

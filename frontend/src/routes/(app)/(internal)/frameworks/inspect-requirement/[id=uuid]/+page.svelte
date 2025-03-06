<script lang="ts">
	import type { PageData } from './$types';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	export let data: PageData;
	console.log(data);

	function findRequirementAssessment(audit: string, requirementAssessments: any[]): any {
		return requirementAssessments.find((ra) => ra.compliance_assessment.id === audit);
	}
</script>

<div class="card px-6 py-4 bg-white flex flex-col justify-center items-center shadow-lg w-full">
	<span class="text-lg font-bold">{data.requirementAssessments[0].name}</span>
	<span class="text-sm text-center">{data.requirementAssessments[0].description}</span>
	{#each data.metrics as domain}
		<Accordion>
			<AccordionItem open>
				<svelte:fragment slot="lead"><i class="fa-solid fa-sitemap"></i></svelte:fragment>
				<svelte:fragment slot="summary"
					><span class="font-bold">{domain.name}</span></svelte:fragment
				>
				<svelte:fragment slot="content">
					<div class="grid grid-cols-3 gap-4">
						{#each domain.perimeters as perimeter}
							<div class="tile p-4 bg-gray-100 shadow-md">
								<span class="font-bold"
									><i class="fa-solid fa-cubes mr-2"></i> {perimeter.name}</span
								>
								<div>
									<p>Compliance Result:</p>
									<div class="flex items-center">
										<span class="text-lg font-bold"
											>{perimeter.compliance_result.compliance_percentage}%</span
										>
										<span class="text-sm ml-2"
											>({perimeter.compliance_result.compliant_count} / {perimeter.compliance_result
												.total_count})</span
										>
									</div>
									<div class="h-2 bg-gray-200 rounded-full mt-2">
										<div
											class="h-full bg-green-500 rounded-full"
											style="width: {perimeter.compliance_result.compliance_percentage}%;"
										></div>
									</div>
								</div>
								<div>
									<p>Assessment Progress:</p>
									<div class="flex items-center">
										<span class="text-lg font-bold"
											>{perimeter.assessment_progress.assessment_completion_rate}%</span
										>
										<span class="text-sm ml-2"
											>({perimeter.assessment_progress.assessed_count} / {perimeter
												.assessment_progress.total_count})</span
										>
									</div>
									<div class="h-2 bg-gray-200 rounded-full mt-2">
										<div
											class="h-full bg-blue-500 rounded-full"
											style="width: {perimeter.assessment_progress.assessment_completion_rate}%;"
										></div>
									</div>
								</div>
								<div>
									<ul>
										{#if perimeter.scoring_metrics.average_score !== null}
											<li>Average Score: {perimeter.scoring_metrics.average_score}</li>
										{/if}
										{#if perimeter.scoring_metrics.average_documentation_score !== null}
											<li>
												Average Documentation Score: {perimeter.scoring_metrics
													.average_documentation_score}
											</li>
										{/if}
									</ul>
								</div>
								<div>
									<p>Compliance Assessments:</p>
									<ul>
										{#each perimeter.compliance_assessments as assessment}
											<li>
												<Anchor
													breadcrumbAction="push"
													href="/compliance-assessments/{assessment.id}/"
													class="anchor">{assessment.name}</Anchor
												>:
												<Anchor
													breadcrumbAction="push"
													href="/requirement-assessments/{findRequirementAssessment(
														assessment.id,
														data.requirementAssessments
													).id}/"
													class="anchor"
												>
													See Requirement Assessment
												</Anchor>
											</li>
										{/each}
									</ul>
								</div>
							</div>
						{/each}
					</div>
				</svelte:fragment>
			</AccordionItem>
		</Accordion>
	{/each}
</div>

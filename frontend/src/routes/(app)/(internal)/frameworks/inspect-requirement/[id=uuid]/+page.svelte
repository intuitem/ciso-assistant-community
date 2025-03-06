<script lang="ts">
	import type { PageData } from './$types';
	import { Accordion, AccordionItem } from '@skeletonlabs/skeleton';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';
	import { safeTranslate } from '$lib/utils/i18n';
	import { darkenColor } from '$lib/utils/helpers';
    import { page } from '$app/stores';

	export let data: PageData;

	function findRequirementAssessment(audit: string, requirementAssessments: any[]): any {
		return requirementAssessments.find((ra) => ra.compliance_assessment.id === audit);
	}
</script>

<div
	class="card px-6 py-4 bg-white flex flex-col justify-center items-center shadow-lg w-full rounded-lg"
>
    {#if data.requirementAssessments.length > 0}
        <span class="text-2xl font-bold text-gray-800">{data.requirementAssessments[0].name}</span>
        <span class="text-sm text-center text-gray-600">{data.requirementAssessments[0].description}</span
        >
        {#each data.metrics as domain}
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
                            {#each domain.perimeters as perimeter}
                                <div class="tile p-4 bg-gray-100 shadow-md rounded-lg">
                                    <span class="font-bold text-lg text-gray-800"
                                        ><i class="fa-solid fa-cubes mr-2 text-primary-500"></i> {perimeter.name}</span
                                    >
                                    <div>
                                        <p class="text-gray-600">Compliant Requirements:</p>
                                        <div class="flex items-center">
                                            <span class="text-xl font-bold text-green-500"
                                                >{perimeter.compliance_result.compliance_percentage}%</span
                                            >
                                            <span class="text-sm ml-2 text-gray-600"
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
                                        <p class="text-gray-600">Requirements Progression:</p>
                                        <div class="flex items-center">
                                            <span class="text-xl font-bold text-blue-500"
                                                >{perimeter.assessment_progress.assessment_completion_rate}%</span
                                            >
                                            <span class="text-sm ml-2 text-gray-600"
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
                                        <ul class="list-disc list-inside text-gray-600">
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
                                        <p class="text-gray-600">Compliance Assessments:</p>
                                        <ul class="list-disc list-inside text-gray-600 space-y-1">
                                            {#each perimeter.compliance_assessments as assessment}
                                                {@const requirementAssessment = findRequirementAssessment(
                                                    assessment.id,
                                                    data.requirementAssessments
                                                )}
                                                <li class="flex items-center space-x-2">
                                                    <Anchor
                                                        breadcrumbAction="push"
                                                        href="/compliance-assessments/{assessment.id}?next={$page.url.pathname}"
                                                        label={assessment.name}
                                                        class="anchor whitespace-nowrap"
                                                    >
                                                        {#if assessment.name.length > 12}
                                                            {assessment.name.slice(0, 12)}...
                                                        {:else}
                                                            {assessment.name}
                                                        {/if}
                                                    </Anchor>:
                                                    <Anchor
                                                        breadcrumbAction="push"
                                                        href="/requirement-assessments/{requirementAssessment.id}?next={$page.url.pathname}"
                                                        label={requirementAssessment.name}
                                                        class="anchor whitespace-nowrap"
                                                    >
                                                        Requirement link
                                                    </Anchor>
                                                    <span
                                                        class="badge h-fit whitespace-nowrap"
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
                                                        class="badge h-fit whitespace-nowrap"
                                                        style="background-color: {complianceResultColorMap[
                                                            requirementAssessment.result
                                                        ] + '44'}; color: {darkenColor(
                                                            complianceResultColorMap[requirementAssessment.result],
                                                            0.3
                                                        )};"
                                                    >
                                                        {safeTranslate(requirementAssessment.result)}
                                                    </span>
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
    {:else}
        <div class="flex flex-col items-center justify-center h-full">
            <div class="text-center">
                <h1 class="text-2xl font-bold">No requirements found</h1>
                <p class="text-gray-500">There is no audit for this framework.</p>
            </div>
        </div>
    {/if}
</div>

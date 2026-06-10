<script lang="ts">
	import * as m from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { complianceResultColorMap } from '$lib/utils/constants';

	interface SourceFramework {
		id: string;
		name: string;
	}

	interface UsedMappingSet {
		id: string | null;
		urn: string | null;
		name: string | null;
		ref_id: string | null;
		library_urn: string | null;
	}

	interface MappedRequirementAssessmentInfo {
		urn: string;
		id: string | null;
		str: string | null;
		is_scored: boolean | null;
		score?: number | null;
		coverage: 'full' | 'partial' | 'not_related';
		source_framework?: SourceFramework;
		used_mapping_set?: UsedMappingSet;
	}

	type RequirementAssessmentURN = string;

	type SourceRequirementAssessments = Record<
		RequirementAssessment,
		MappedRequirementAssessmentInfo
	>;

	interface MappingInference {
		result:
			| 'not_assessed'
			| 'partially_compliant'
			| 'non_compliant'
			| 'compliant'
			| 'not_applicable';
		annotation?: string | null;
		source_requirement_assessments: SourceRequirementAssessments;
		[key: string]: unknown; // (There are other fields unused by this component)
	}

	interface Props {
		mappingInference: MappingInference;
	}

	let { mappingInference }: Props = $props();

	let sourceRequirementAssessmentCount = $derived(Object.keys(mappingInference.source_requirement_assessments).length);

	let expandedInferences = $state(false);
</script>

<div class="my-2">
	<p class="font-medium">
		<i class="fa-solid fa-link"></i>
		{m.mappingInference()}
	</p>
	<span class="text-xs text-gray-500"
		><i class="fa-solid fa-circle-info"></i> {m.mappingInferenceHelpText()}</span
	>
	<button
		onclick={() => (expandedInferences = !expandedInferences)}
		class="block mt-2 text-blue-800"
		aria-expanded={expandedInferences}
	>
		<i class="h-full {expandedInferences ? 'fas fa-chevron-up' : 'fas fa-chevron-down'}"></i>
		{#if expandedInferences}
			{m.hideInferences()}
		{:else}
			{m.showInferences()}
		{/if}
		({sourceRequirementAssessmentCount})
	</button>
	<ol class="ml-0 {!expandedInferences ? 'hidden' : ''}">
		{#each Object.entries(mappingInference.source_requirement_assessments) as [source_urn, source_requirement_assessment], index}
			<li class="p-2 border-2 border-b-primary-500">
				<div class="mb-1">
					{#if source_requirement_assessment.id}
						<a
							class="anchor code"
							href="/requirement-assessments/{source_requirement_assessment.id}"
						>
							{index + 1}. {source_requirement_assessment.str}
						</a>
					{:else}
						<span class="code">
							{index + 1}. {source_requirement_assessment.str}
						</span>
					{/if}
				</div>
				<div class="grid grid-cols-[6rem_1fr] items-center">
					<span class="font-medium">{m.coverageColon()}</span>
					<span class="badge py-0 h-fit w-fit">
						{safeTranslate(source_requirement_assessment.coverage)}
					</span>

					{#if source_requirement_assessment.source_framework}
						<span class="font-medium">{m.framework()}:</span>
						<a
							class="anchor badge py-0 h-fit w-fit"
							href="/frameworks/{source_requirement_assessment.source_framework.id}"
						>
							{source_requirement_assessment.source_framework.name}
						</a>
					{/if}

					{#if source_requirement_assessment.used_mapping_set}
						<span class="font-medium">{m.mapping()}:</span>
						<a
							class="anchor badge py-0 h-fit w-fit"
							href="/requirement-mapping-sets/{source_requirement_assessment.used_mapping_set?.id}"
						>
							{source_requirement_assessment.used_mapping_set?.name}
						</a>
					{:else}
						<span class="text-gray-500">--</span>
					{/if}

					{#if source_requirement_assessment.is_scored}
						<span class="font-medium">{m.scoreSemiColon()}</span>
						<span class="badge py-0 h-fit w-fit">
							{safeTranslate(source_requirement_assessment.score)}
						</span>
					{/if}

					<span class="font-medium">{m.suggestionColon()}</span>
					<span
						class="badge py-0 h-fit w-fit"
						style="background-color: {complianceResultColorMap[mappingInference.result]};"
					>
						{safeTranslate(mappingInference.result)}
					</span>

					{#if mappingInference.annotation}
						<span class="font-medium">{m.annotationColon()}</span>
						<span>{mappingInference.annotation}</span>
					{/if}
				</div>
			</li>
		{/each}
	</ol>
</div>

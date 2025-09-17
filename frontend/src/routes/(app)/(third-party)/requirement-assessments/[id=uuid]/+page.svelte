<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';
	import {
		displayScoreColor,
		formatScoreValue,
		getRequirementTitle,
		getSecureRedirect
	} from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales';
	import { hideSuggestions } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { ProgressRing, Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from '../[id=uuid]/$types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const threats = data.requirementAssessment.requirement.associated_threats ?? [];
	const reference_controls =
		data.requirementAssessment.requirement.associated_reference_controls ?? [];
	const annotation = data.requirement.annotation;
	const typical_evidence = data.requirement.typical_evidence;

	const has_threats = threats.length > 0;
	const has_reference_controls = reference_controls.length > 0;

	let mappingInference = $derived({
		sourceRequirementAssessment:
			data.requirementAssessment.mapping_inference.source_requirement_assessment,
		result: data.requirementAssessment.mapping_inference.result,
		annotation: ''
	});

	const title = getRequirementTitle(data.requirement.ref_id, data.requirement.name)
		? getRequirementTitle(data.requirement.ref_id, data.requirement.name)
		: getRequirementTitle(data.parent.ref_id, data.parent.name);

	let requirementAssessmentsList: string[] = $hideSuggestions;

	let hideSuggestion = $state(
		requirementAssessmentsList.includes(data.requirementAssessment.id) ? true : false
	);

	function toggleSuggestions() {
		if (!requirementAssessmentsList.includes(data.requirementAssessment.id)) {
			requirementAssessmentsList.push(data.requirementAssessment.id);
		} else {
			requirementAssessmentsList = requirementAssessmentsList.filter(
				(item) => item !== data.requirementAssessment.id
			);
		}
		hideSuggestion = !hideSuggestion;
		hideSuggestions.set(requirementAssessmentsList);
	}

	function cancel(): void {
		const AuditURL = `/compliance-assessments/${data.requirementAssessment.compliance_assessment.id}`;
		goto(AuditURL);
	}

	let classesText = $derived(
		complianceResultColorMap[mappingInference.result] === '#000000' ? 'text-white' : ''
	);

	const max_score = data.complianceAssessmentScore.max_score;
	const score = data.requirementAssessment.score;
	const documentationScore = data.requirementAssessment.documentation_score;

	let group = $state(page.data.user.is_third_party ? 'evidence' : 'applied_controls');
</script>

<div class="card space-y-2 p-4 bg-white shadow-sm">
	<div class="flex flex-row space-x-2 items-center">
		<code class="code">{data.requirement.urn}</code>
		<span
			class="badge h-fit"
			style="background-color: {complianceStatusColorMap[data.requirementAssessment.status] ??
				'#d1d5db'};"
		>
			{safeTranslate(data.requirementAssessment.status)}
		</span>
		<span
			class="badge {classesText} h-fit"
			style="background-color: {complianceResultColorMap[data.requirementAssessment.result] ??
				'#d1d5db'};"
		>
			{safeTranslate(data.requirementAssessment.result)}
		</span>
		{#if data.requirementAssessment.is_scored}
			<ProgressRing
				strokeWidth="20px"
				meterStroke={displayScoreColor(score, max_score)}
				value={formatScoreValue(score, max_score)}
				classes="shrink-0"
				size="size-10">{score}</ProgressRing
			>
			{#if data.complianceAssessmentScore.show_documentation_score}
				<ProgressRing
					strokeWidth="20px"
					meterStroke={displayScoreColor(documentationScore, max_score)}
					value={formatScoreValue(documentationScore, max_score)}
					classes="shrink-0"
					size="size-10">{documentationScore}</ProgressRing
				>
			{/if}
		{/if}
	</div>
	{#if data.requirement.description}
		<div class="font-light text-lg card p-4 preset-tonal-primary">
			<h2 class="font-semibold text-base flex flex-row justify-between">
				<div>
					<i class="fa-solid fa-file-lines mr-2"></i>{m.description()}
				</div>
			</h2>
			<MarkdownRenderer content={data.requirement.description} />
		</div>
	{/if}
	{#if has_threats || has_reference_controls || annotation || mappingInference.result}
		<div class="card p-4 preset-tonal-secondary text-sm flex flex-col justify-evenly cursor-auto">
			<h2 class="font-semibold text-base flex flex-row justify-between">
				<div>
					<i class="fa-solid fa-circle-info mr-2"></i>{m.additionalInformation()}
				</div>
				<button onclick={toggleSuggestions}>
					{#if !hideSuggestion}
						<i class="fa-solid fa-eye"></i>
					{:else}
						<i class="fa-solid fa-eye-slash"></i>
					{/if}
				</button>
			</h2>
			{#if !hideSuggestion}
				{#if has_threats || has_reference_controls}
					<div class="my-2 flex flex-col">
						<div class="flex-1">
							{#if reference_controls.length > 0}
								<p class="font-medium">
									<i class="fa-solid fa-gears"></i>
									{m.suggestedReferenceControls()}
								</p>
								<ul class="list-disc ml-4">
									{#each reference_controls as func}
										<li>
											{#if func.id}
												<a class="anchor" href="/reference-controls/{func.id}">
													{func.str}
												</a>
											{:else}
												<p>{func.str}</p>
											{/if}
										</li>
									{/each}
								</ul>
							{/if}
						</div>
						<div class="flex-1">
							{#if threats.length > 0}
								<p class="font-medium">
									<i class="fa-solid fa-gears"></i>
									{m.threatsCovered()}
								</p>
								<ul class="list-disc ml-4">
									{#each threats as threat}
										<li>
											{#if threat.id}
												<a class="anchor" href="/threats/{threat.id}">
													{threat.str}
												</a>
											{:else}
												<p>{threat.str}</p>
											{/if}
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					</div>
				{/if}
				{#if annotation}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-pencil"></i>
							{m.annotation()}
						</p>
						<div class="py-1">
							<MarkdownRenderer content={annotation} />
						</div>
					</div>
				{/if}
				{#if typical_evidence}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-pencil"></i>
							{m.typicalEvidence()}
						</p>
						<div class="py-1">
							<MarkdownRenderer content={typical_evidence} />
						</div>
					</div>
				{/if}
				{#if mappingInference.result}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-link"></i>
							{m.mappingInference()}
						</p>
						<span class="text-xs text-gray-500"
							><i class="fa-solid fa-circle-info"></i> {m.mappingInferenceHelpText()}</span
						>
						<ul class="list-disc ml-4">
							<li>
								<p>
									<a
										class="anchor"
										href="/requirement-assessments/{mappingInference.sourceRequirementAssessment
											.id}"
									>
										{mappingInference.sourceRequirementAssessment.str}
									</a>
								</p>
								<p class="whitespace-pre-line py-1">
									<span class="italic">{m.coverageColon()}</span>
									<span class="badge h-fit">
										{safeTranslate(
											toCamelCase(mappingInference.sourceRequirementAssessment.coverage)
										)}
									</span>
								</p>
								<p class="whitespace-pre-line py-1">
									<span class="italic">{m.suggestionColon()}</span>
									<span
										class="badge {classesText} h-fit"
										style="background-color: {complianceResultColorMap[mappingInference.result]};"
									>
										{safeTranslate(mappingInference.result)}
									</span>
								</p>
								{#if mappingInference.annotation}
									<p class="whitespace-pre-line py-1">
										<span class="italic">{m.annotationColon()}</span>
										{mappingInference.annotation}
									</p>
								{/if}
							</li>
						</ul>
					</div>
				{/if}
			{/if}
		</div>
	{/if}
	<div>
		<Tabs
			value={group}
			onValueChange={(e) => {
				group = e.value;
			}}
		>
			{#snippet list()}
				{#if !page.data.user.is_third_party}
					<Tabs.Control value="applied_controls">{m.appliedControls()}</Tabs.Control>
				{/if}
				<Tabs.Control value="evidence">{m.evidences()}</Tabs.Control>
			{/snippet}
			{#snippet content()}
				<Tabs.Panel value="applied_controls">
					{#if !page.data.user.is_third_party}
						<div class="flex items-center mb-2 px-2 text-xs space-x-2">
							<i class="fa-solid fa-info-circle"></i>
							<p>{m.requirementAppliedControlHelpText()}</p>
						</div>
						<div class="h-full flex flex-col space-y-2 rounded-container p-4">
							<ModelTable
								source={data.tables['applied-controls']}
								hideFilters={true}
								URLModel="applied-controls"
								baseEndpoint="/applied-controls?requirement_assessments={page.data
									.requirementAssessment.id}"
							/>
						</div>
					{/if}
				</Tabs.Panel>
				<Tabs.Panel value="evidence">
					<div class="flex items-center mb-2 px-2 text-xs space-x-2">
						<i class="fa-solid fa-info-circle"></i>
						<p>{m.requirementEvidenceHelpText()}</p>
					</div>
					<div class="h-full flex flex-col space-y-2 rounded-container p-4">
						<ModelTable
							source={data.tables['evidences']}
							hideFilters={true}
							URLModel="evidences"
							baseEndpoint="/evidences?requirement_assessments={page.data.requirementAssessment.id}"
						/>
					</div>
				</Tabs.Panel>
			{/snippet}
		</Tabs>
	</div>
	{#if data.requirementAssessment.requirement.questions != null && Object.keys(data.requirementAssessment.requirement.questions).length !== 0}
		<h1 class="font-semibold text-sm">{m.questions()}</h1>
		{#each Object.entries(data.requirementAssessment.requirement.questions) as [urn, question]}
			<li class="flex justify-between items-center border rounded-xl p-2 disabled">
				<p>{question.text} ({safeTranslate(question.type)})</p>
			</li>
		{/each}
	{/if}
	{#if data.requirementAssessment.observation}
		<div class="card p-4 space-y-2 preset-tonal-primary">
			<h1 class="font-semibold text-sm">{m.observation()}</h1>
			<div class="text-sm">
				<MarkdownRenderer content={data.requirementAssessment.observation} />
			</div>
		</div>
	{/if}
	<div class="flex flex-row justify-between space-x-4">
		<button class="btn bg-gray-400 text-white font-semibold w-full" type="button" onclick={cancel}
			>{m.back()}</button
		>
	</div>
</div>

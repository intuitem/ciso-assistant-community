<script lang="ts">
	import { page } from '$app/state';
	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';
	import { darkenColor } from '$lib/utils/helpers';
	import type { ReferenceControlSchema, ThreatSchema } from '$lib/utils/schemas';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { z } from 'zod';
	import { m } from '$paraglide/messages';
	import { auditFiltersStore } from '$lib/utils/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { isQuestionVisible } from '$lib/utils/helpers';

	interface Props {
		ref_id: string;
		name: string;
		description: string;
		ra_id?: string | undefined;
		threats?: z.infer<typeof ThreatSchema>[] | undefined;
		reference_controls?: z.infer<typeof ReferenceControlSchema>[] | undefined;
		children?: Record<string, Record<string, unknown>> | undefined;
		canEditRequirementAssessment: boolean;
		hasParentNode: boolean;
		showDocumentationScore: boolean;
		scoreCalculationMethod: string;
		selectedStatus: string[];
		resultCounts: Record<string, number> | undefined;
		assessable: boolean;
		max_score: number;
		[key: string]: any;
	}

	let {
		ref_id,
		name,
		description,
		ra_id = undefined,
		threats = undefined,
		reference_controls = undefined,
		children = undefined,
		canEditRequirementAssessment,
		hasParentNode,
		showDocumentationScore,
		scoreCalculationMethod,
		selectedStatus,
		resultCounts,
		assessable,
		max_score,
		...rest
	}: Props = $props();

	const node = {
		ref_id,
		name,
		description,
		ra_id,
		threats,
		reference_controls,
		children,
		canEditRequirementAssessment,
		max_score,
		resultCounts,
		assessable,
		...rest
	} as const;

	type TreeViewItemNode = typeof node;

	const pattern = (ref_id ? 2 : 0) + (name ? 1 : 0);
	const title: string =
		pattern == 3 ? `${ref_id} - ${name}` : pattern == 2 ? ref_id : pattern == 1 ? name : '';

	let showInfo = $state(false);

	let id = page.params.id;
	let displayOnlyAssessableNodes = $derived(
		$auditFiltersStore[id]?.displayOnlyAssessableNodes ?? false
	);

	const getAssessableNodes = (
		startNode: TreeViewItemNode,
		assessableNodes: TreeViewItemNode[] = []
	) => {
		if (startNode.assessable) assessableNodes.push(startNode);
		if (startNode.children) {
			for (const value of Object.values(startNode.children) as TreeViewItemNode[]) {
				getAssessableNodes(value, assessableNodes);
			}
		}
		return assessableNodes;
	};

	const assessableNodes = getAssessableNodes(node);
	const hasAssessableChildren =
		children &&
		Object.keys(children).length > 0 &&
		assessableNodes.length - (node.assessable ? 1 : 0) > 0;

	const REQUIREMENT_ASSESSMENT_RESULT = [
		'compliant',
		'non_compliant',
		'partially_compliant',
		'not_applicable'
	] as const;

	type ResultPercentage = {
		result: (typeof REQUIREMENT_ASSESSMENT_RESULT)[number];
		percentage: {
			value: number;
			display: string;
		};
	};

	const orderedResultPercentages: ResultPercentage[] = REQUIREMENT_ASSESSMENT_RESULT.map(
		(result) => {
			if (!resultCounts) return { result: result, percentage: { value: 0, display: '0' } };
			const value = resultCounts[result] || 0;
			const percentValue: number = (value / assessableNodes.length) * 100;
			const percentage = {
				value: percentValue,
				display: percentValue.toFixed(0)
			};
			return { result: result, percentage };
		}
	);

	function nodeScore(): number | null {
		if (
			!resultCounts ||
			!resultCounts.hasOwnProperty('total_score') ||
			!resultCounts.hasOwnProperty('total_weight')
		) {
			return null;
		}
		if (scoreCalculationMethod === 'sum') {
			return Math.floor(resultCounts['total_score'] * 10) / 10;
		}
		// Default to weighted average
		let mean = resultCounts['total_score'] / resultCounts['total_weight'];
		return Math.floor(mean * 10) / 10;
	}

	function nodeDocumentationScore(): number | null {
		if (
			!resultCounts ||
			!resultCounts.hasOwnProperty('total_documentation_score') ||
			!resultCounts.hasOwnProperty('total_weight')
		) {
			return null;
		}
		if (scoreCalculationMethod === 'sum') {
			return Math.floor(resultCounts['total_documentation_score'] * 10) / 10;
		}
		// Default to weighted average
		let mean = resultCounts['total_documentation_score'] / resultCounts['total_weight'];
		return Math.floor(mean * 10) / 10;
	}

	function nodeTotalMaxScore(): number {
		// For SUM, the total max is max_score * total_weight
		// For AVG, the total max is just max_score
		if (scoreCalculationMethod === 'sum' && resultCounts?.total_weight) {
			return node.max_score * resultCounts['total_weight'];
		}
		return node.max_score;
	}

	let classesShowInfo = $derived((show: boolean) => (!show ? 'hidden' : ''));
	let classesShowInfoText = $derived((show: boolean) => (show ? 'text-primary-500' : ''));
	let classesPercentText = $derived((resultColor: string) =>
		resultColor === '#000000' ? 'text-white' : 'text-gray-900'
	);

	export const getBadgeStyles = (answers: any, questions: any) => {
		const visibleQuestions = Object.entries(questions || {}).filter(([_, q]) =>
			isQuestionVisible(q, answers)
		);

		const answeredCount = visibleQuestions.filter(([urn, _]) => {
			const answer = answers[urn];
			if (Array.isArray(answer)) return answer.length > 0;
			return answer !== null && answer !== undefined && answer !== '';
		}).length;

		const totalCount = visibleQuestions.length;

		const backgroundColor =
			answeredCount === 0 ? '#fca5a5' : answeredCount === totalCount ? '#bbf7d0' : '#fef08a';

		return {
			backgroundColor,
			color: darkenColor(backgroundColor, 0.6),
			answeredCount,
			totalCount
		};
	};
</script>

{#if !displayOnlyAssessableNodes || assessable || hasAssessableChildren}
	<div class="flex flex-row justify-between space-x-8">
		<div class="flex flex-1 justify-center max-w-[80ch] flex-col">
			<div class="flex flex-row space-x-2 items-center" style="font-weight: 300;">
				<div>
					{#if assessable}
						<span class="w-full h-full flex rounded-base hover:text-primary-500">
							{#if canEditRequirementAssessment}
								<Anchor
									breadcrumbAction="push"
									href="/requirement-assessments/{ra_id}/edit?next={page.url.pathname}"
								>
									{#if title || description}
										{#if title}
											<span style="font-weight: 600;">{title}</span>
										{/if}
										{#if description}
											<MarkdownRenderer content={description} />
										{/if}
									{:else if Object.keys(node.questions).length > 0}
										<!-- This displays the first question's text -->
										{Object.entries(node.questions)[0][1].text}
									{/if}
								</Anchor>
							{:else}
								<Anchor
									breadcrumbAction="push"
									href="/requirement-assessments/{ra_id}?next={page.url.pathname}"
								>
									{#if title}
										<span style="font-weight: 600;">{title}</span>
									{/if}
									{#if description}
										<MarkdownRenderer content={description} />
									{/if}
								</Anchor>
							{/if}
						</span>
					{:else}
						<p class="max-w-[80ch] whitespace-pre-line">
							{#if title}
								<span style="font-weight: 600;">{title}</span>
							{/if}
							{#if description}
								<MarkdownRenderer content={description} />
							{/if}
						</p>
					{/if}
				</div>
				{#if !assessable}
					<div class="flex flex-row items-end items-middle text-xs mr-2" style="width:6rem">
						{#each orderedResultPercentages as rp}
							{#if resultCounts && resultCounts[rp.result] !== undefined}
								<div
									class="rounded-md px-1 mx-1 leading-4"
									style="background-color: {complianceResultColorMap[
										rp.result
									]}; color: {complianceResultColorMap[rp.result] === '#000000'
										? '#ffffff'
										: '#111827'}"
								>
									{resultCounts[rp.result]}
								</div>
							{/if}
						{/each}
						{#if resultCounts && resultCounts['not_assessed'] !== undefined}
							<div
								class="rounded-md px-1 mx-1 leading-4"
								style="background-color: {complianceResultColorMap[
									'not_assessed'
								]}; color: {complianceResultColorMap['not_assessed'] === '#000000'
									? '#ffffff'
									: '#111827'}"
							>
								{resultCounts['not_assessed']}
							</div>
						{/if}
					</div>
				{/if}
				<div>
					{#if hasAssessableChildren}
						{#each Object.entries(complianceStatusColorMap) as [status, color]}
							{#if resultCounts?.status && (selectedStatus.includes(status) || selectedStatus.length === 0)}
								<span
									class="badge mr-1"
									style="background-color: {color + '44'}; color: {darkenColor(color, 0.3)}"
								>
									{resultCounts[status]}
									{safeTranslate(status)}
								</span>
							{/if}
						{/each}
					{/if}
					{#if node.questions}
						{@const badgeStyles = getBadgeStyles(node.answers, node.questions)}
						<span
							class="badge"
							style="background-color: {badgeStyles.backgroundColor}; color: {badgeStyles.color}"
						>
							{badgeStyles.answeredCount}/{badgeStyles.totalCount}
							{Object.keys(node.questions).length > 1 ? m.questionPlural() : m.questionSingular()}
						</span>
					{/if}
				</div>
			</div>
		</div>
		{#if (threats && threats.length > 0) || (reference_controls && reference_controls.length > 0)}
			<div
				role="button"
				tabindex="0"
				class="select-none text-sm hover:text-primary-400 {classesShowInfoText(showInfo)}"
				onclick={(e) => {
					e.preventDefault();
					showInfo = !showInfo;
				}}
				onkeydown={(e) => {
					if (e.key === 'Enter') {
						e.preventDefault();
						showInfo = !showInfo;
					}
				}}
			>
				<i class="text-xs fa-solid fa-info-circle"></i> Learn more
			</div>
			<div
				class="card p-2 preset-tonal-primary border border-primary-500 text-sm flex flex-row cursor-auto {classesShowInfo(
					showInfo
				)}"
			>
				<div class="flex-1">
					<p class="font-medium">
						<i class="fa-solid fa-gears"></i>
						Suggested reference controls
					</p>
					{#if reference_controls?.length === 0}
						<p>--</p>
					{:else if reference_controls}
						<ul class="list-disc ml-4">
							{#each reference_controls as func}
								<li>
									{#if func.id}
										<a class="anchor" href="/reference-controls/{func.id}?next={page.url.pathname}">
											{func.name}
										</a>
									{:else}
										<p>{func.name}</p>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
				</div>
				<div class="flex-1">
					<p class="font-medium">
						<i class="fa-solid fa-gears"></i>
						Threats covered
					</p>
					{#if threats?.length === 0}
						<p>--</p>
					{:else if threats}
						<ul class="list-disc ml-4">
							{#each threats as threat}
								<li>
									{#if threat.id}
										<a class="anchor" href="/threats/{threat.id}?next={page.url.pathname}">
											{threat.name}
										</a>
									{:else}
										<p>{threat.name}</p>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			</div>
		{/if}
		{#if hasAssessableChildren}
			<div class="flex max-w-96 grow items-center space-x-2">
				<div
					class="flex max-w-96 grow bg-surface-200-800 rounded-full overflow-hidden h-4 shrink self-center"
				>
					{#each orderedResultPercentages as rp}
						<div
							class="flex flex-col justify-center overflow-hidden text-xs text-center {classesPercentText(
								complianceResultColorMap[rp.result]
							)}"
							style="width: {rp.percentage.value}%; background-color: {complianceResultColorMap[
								rp.result
							]}"
						>
							{rp.percentage.display}%
						</div>
					{/each}
				</div>
				<div class="flex flex-row space-x-2 items-center">
					{#if hasParentNode}
						{#if nodeScore() !== null}
							<ProgressRing
								strokeWidth="20px"
								value={formatScoreValue(nodeScore(), nodeTotalMaxScore())}
								meterStroke={displayScoreColor(nodeScore(), nodeTotalMaxScore())}
								size="size-12">{nodeScore()}</ProgressRing
							>
							{#if showDocumentationScore}
								<ProgressRing
									strokeWidth="20px"
									value={formatScoreValue(nodeDocumentationScore(), nodeTotalMaxScore())}
									meterStroke={displayScoreColor(nodeDocumentationScore(), nodeTotalMaxScore())}
									size="size-12">{nodeDocumentationScore()}</ProgressRing
								>
							{/if}
						{/if}
					{:else if nodeScore() !== null}
						<ProgressRing
							strokeWidth="20px"
							value={formatScoreValue(nodeScore(), nodeTotalMaxScore())}
							meterStroke={displayScoreColor(nodeScore(), nodeTotalMaxScore())}
							size="size-12">{nodeScore()}</ProgressRing
						>
						{#if showDocumentationScore}
							<ProgressRing
								strokeWidth="20px"
								value={formatScoreValue(nodeDocumentationScore(), nodeTotalMaxScore())}
								meterStroke={displayScoreColor(nodeDocumentationScore(), nodeTotalMaxScore())}
								size="size-12">{nodeDocumentationScore()}</ProgressRing
							>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}

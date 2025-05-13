<script lang="ts">
	import { page } from '$app/stores';
	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';
	import { darkenColor } from '$lib/utils/helpers';
	import type { ReferenceControlSchema, ThreatSchema } from '$lib/utils/schemas';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { z } from 'zod';
	import { m } from '$paraglide/messages';
	import { displayOnlyAssessableNodes } from './store';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		ref_id: string;
		name: string;
		description: string;
		ra_id?: string | undefined;
		threats?: z.infer<typeof ThreatSchema>[] | undefined;
		reference_controls?: z.infer<typeof ReferenceControlSchema>[] | undefined;
		children?: Record<string, Record<string, unknown>> | undefined;
		canEditRequirementAssessment: boolean;
		selectedStatus: string[];
		resultCounts: Record<string, number> | undefined;
		assessable: boolean;
		max_score: number;
		[key: string]: any
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
		if (!resultCounts) return null;
		let mean = resultCounts['total_score'] / resultCounts['scored'];
		return Math.floor(mean * 10) / 10;
	}

	let classesShowInfo = $derived((show: boolean) => (!show ? 'hidden' : ''));
	let classesShowInfoText = $derived((show: boolean) => (show ? 'text-primary-500' : ''));
	let classesPercentText = $derived((resultColor: string) => (resultColor === '#000000' ? 'text-white' : ''));
</script>

{#if !$displayOnlyAssessableNodes || assessable || hasAssessableChildren}
	<div class="flex flex-row justify-between space-x-8">
		<div class="flex flex-1 justify-center max-w-[80ch] flex-col">
			<div class="flex flex-row space-x-2" style="font-weight: 300;">
				<div>
					{#if assessable}
						<span class="w-full h-full flex rounded-token hover:text-primary-500">
							{#if canEditRequirementAssessment}
								<Anchor
									breadcrumbAction="push"
									href="/requirement-assessments/{ra_id}/edit?next={$page.url.pathname}"
								>
									{#if title || description}
										{#if title}
											<span style="font-weight: 600;">{title}</span>
										{/if}
										{#if description}
											<p>{description}</p>
										{/if}
									{:else if Object.keys(node.questions).length > 0}
										<!-- This displays the first question's text -->
										{Object.entries(node.questions)[0][1].text}
									{/if}
								</Anchor>
							{:else}
								<Anchor
									breadcrumbAction="push"
									href="/requirement-assessments/{ra_id}?next={$page.url.pathname}"
								>
									{#if title}
										<span style="font-weight: 600;">{title}</span>
									{/if}
									{#if description}
										<p>{description}</p>
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
								<p>{description}</p>
							{/if}
						</p>
					{/if}
				</div>
				<div>
					{#if hasAssessableChildren}
						{#each Object.entries(complianceStatusColorMap) as [status, color]}
							{#if resultCounts[status] && selectedStatus.includes(status)}
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
						{#if Object.keys(node.questions).length > 1}
							<span
								class="badge"
								style="background-color: pink; color: {darkenColor('#FFC0CB', 0.5)}"
								>{Object.keys(node.questions).length} {m.questionPlural()}</span
							>
						{:else}
							<span
								class="badge"
								style="background-color: pink; color: {darkenColor('#FFC0CB', 0.5)}"
								>{Object.keys(node.questions).length} {m.questionSingular()}</span
							>
						{/if}
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
				class="card p-2 variant-ghost-primary text-sm flex flex-row cursor-auto {classesShowInfo(
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
										<a
											class="anchor"
											href="/reference-controls/{func.id}?next={$page.url.pathname}"
										>
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
										<a class="anchor" href="/threats/{threat.id}?next={$page.url.pathname}">
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
					class="flex max-w-96 grow bg-gray-200 rounded-full overflow-hidden h-4 shrink self-center"
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
				{#if nodeScore() !== null}
					<span>
						<ProgressRadial
							stroke={100}
							meter={displayScoreColor(nodeScore(), node.max_score)}
							font={150}
							value={formatScoreValue(nodeScore(), node.max_score)}
							width={'w-10'}>{nodeScore()}</ProgressRadial
						>
					</span>
				{/if}
			</div>
		{/if}
	</div>
{/if}

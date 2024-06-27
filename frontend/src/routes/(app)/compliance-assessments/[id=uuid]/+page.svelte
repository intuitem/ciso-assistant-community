<script lang="ts">
	import { page } from '$app/stores';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import { breadcrumbObject } from '$lib/utils/stores';
	import type { PopupSettings, TreeViewNode } from '@skeletonlabs/skeleton';
	import { popup } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import TreeViewItemLead from './TreeViewItemLead.svelte';

	import { complianceColorMap } from './utils';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import type { Node } from './types';

	import * as m from '$paraglide/messages';
	import { localItems, toCamelCase } from '$lib/utils/locales';

	export let data: PageData;
	breadcrumbObject.set(data.compliance_assessment);
	const tree = data.tree;

	const compliance_assessment_donut_values = data.compliance_assessment_donut_values;

	const user = $page.data.user;
	const model = URL_MODEL_MAP['compliance-assessments'];
	const canEditObject: boolean = Object.hasOwn(user.permissions, `change_${model.name}`);
	const requirementAssessmentModel = URL_MODEL_MAP['requirement-assessments'];
	const canEditRequirementAssessment: boolean = Object.hasOwn(
		user.permissions,
		`change_${requirementAssessmentModel.name}`
	);

	const countStatus = (
		node: Node,
		statusCounts: Record<string, number> = {}
	): Record<string, number> => {
		if (node.status && node.assessable) {
			statusCounts[node.status] = (statusCounts[node.status] || 0) + 1;
		}
		if (node.is_scored && node.assessable && node.status !== 'not_applicable') {
			statusCounts['scored'] = (statusCounts['scored'] || 0) + 1;
			statusCounts['total_score'] = (statusCounts['total_score'] || 0) + node.score;
		}

		if (node.children && Object.keys(node.children).length > 0) {
			for (const childId in node.children) {
				if (Object.prototype.hasOwnProperty.call(node.children, childId)) {
					const childNode = node.children[childId];
					countStatus(childNode, statusCounts);
				}
			}
		}
		return statusCounts;
	};

	const mappingInference = { results: ['compliant'] };

	function transformToTreeView(nodes: Node[]) {
		return nodes.map(([id, node]) => {
			node.statusCounts = countStatus(node);
			node.mappingInference = mappingInference;
			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: { ...node, canEditRequirementAssessment },
				lead: node.status ? TreeViewItemLead : '',
				leadProps: {
					statusI18n: node.status_i18n,
					assessable: node.assessable,
					statusDisplay: node.status_display,
					statusColor: complianceColorMap[node.status],
					score: node.score,
					isScored: node.is_scored,
					max_score: node.max_score
				},
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[] = transformToTreeView(Object.entries(tree));

	function assessableNodesCount(nodes: TreeViewNode[]): number {
		let count = 0;
		for (const node of nodes) {
			if (node.contentProps.assessable) {
				count++;
			}
			if (node.children) {
				count += assessableNodesCount(node.children);
			}
		}
		return count;
	}

	let expandedNodes: TreeViewNode[] = [];

	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { expandedNodesState } from '$lib/utils/stores';
	import { displayScoreColor } from '$lib/utils/helpers';

	expandedNodes = $expandedNodesState;
	$: expandedNodesState.set(expandedNodes);

	const popupDownload: PopupSettings = {
		event: 'click',
		target: 'popupDownload',
		placement: 'bottom'
	};
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg w-full">
		<div class="flex flex-col space-y-2 whitespace-pre-line w-1/6">
			{#each Object.entries(data.compliance_assessment).filter( ([key, _]) => ['name', 'description', 'project', 'framework', 'authors', 'reviewers', 'status', 'selected_implementation_groups'].includes(key) ) as [key, value]}
				<div class="flex flex-col">
					<div
						class="text-sm font-medium text-gray-800 capitalize-first"
						data-testid={key.replaceAll('_', '-') + '-field-title'}
					>
						{#if key === 'urn'}
							{m.urn()}
						{:else}
							{localItems()[toCamelCase(key)]}
						{/if}
					</div>
					<ul class="text-sm">
						<li
							class="text-gray-600 list-none"
							data-testid={key.replaceAll('_', '-') + '-field-value'}
						>
							{#if value}
								{#if Array.isArray(value)}
									<ul>
										{#each value as val}
											<li>
												{#if val.str && val.id}
													{@const itemHref = `/${
														URL_MODEL_MAP[data.URLModel]['foreignKeyFields']?.find(
															(item) => item.field === key
														)?.urlModel
													}/${val.id}`}
													<a href={itemHref} class="anchor">{val.str}</a>
												{:else}
													{val}
												{/if}
											</li>
										{/each}
									</ul>
								{:else if value.str && value.id}
									{@const itemHref = `/${
										URL_MODEL_MAP['compliance-assessments']['foreignKeyFields']?.find(
											(item) => item.field === key
										)?.urlModel
									}/${value.id}`}
									<a href={itemHref} class="anchor">{value.str}</a>
								{:else if localItems()[toCamelCase(value.str ?? value)]}
									{localItems()[toCamelCase(value.str ?? value)]}
								{:else}
									{value.str ?? value}
								{/if}
							{:else}
								--
							{/if}
						</li>
					</ul>
				</div>
			{/each}
		</div>
		{#if data.global_score.score >= 0}
			<div class="flex items-center">
				<ProgressRadial
					stroke={100}
					meter={displayScoreColor(data.global_score.score, data.global_score.max_score)}
					font={125}
					value={(data.global_score.score * 100) / data.global_score.max_score}
					width={'w-52'}>{data.global_score.score}</ProgressRadial
				>
			</div>
		{/if}
		<div class="w-1/2">
			<DonutChart
				s_label={m.complianceAssessments()}
				name="compliance_assessment"
				values={compliance_assessment_donut_values.values}
				colors={compliance_assessment_donut_values.values.map((object) => object.itemStyle.color)}
			/>
		</div>
		<div class="flex flex-col space-y-2 ml-4">
			<div class="flex flex-row space-x-2">
				<button class="btn variant-filled-primary" use:popup={popupDownload}
					><i class="fa-solid fa-download mr-2" />{m.exportButton()}</button
				>
				<div
					class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1 z-10"
					data-popup="popupDownload"
				>
					<p class="block px-4 py-2 text-sm text-gray-800">{m.complianceAssessment()}</p>

					<a
						href="/compliance-assessments/{data.compliance_assessment.id}/export"
						class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asZIP()}</a
					>
					<p class="block px-4 py-2 text-sm text-gray-800">{m.actionPlan()}</p>
					<a
						href="/compliance-assessments/{data.compliance_assessment.id}/action-plan/export/pdf"
						class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asPDF()}</a
					>
				</div>
				{#if canEditObject}
					<a
						href={`${$page.url.pathname}/edit?next=${$page.url.pathname}`}
						class="btn variant-filled-primary h-fit"
						data-testid="edit-button"><i class="fa-solid fa-pen-to-square mr-2" /> {m.edit()}</a
					>
				{/if}
			</div>
			<a href={`${$page.url.pathname}/action-plan`} class="btn variant-filled-primary h-fit"
				><i class="fa-solid fa-heart-pulse mr-2" />{m.actionPlan()}</a
			>
			<a href={`${$page.url.pathname}/flash-mode`} class="btn text-gray-100 bg-gradient-to-l from-sky-500 to-violet-500 h-fit"
				><i class="fa-solid fa-bolt mr-2"></i> {m.flashMode()}</a
			>
			<button 
				class="btn variant-filled-surface"
				><i class="fa-solid fa-share-nodes mr-2"></i> {m.mapping()}</button
			>
		</div>
	</div>

	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg">
		<h4 class="h4 flex items-center font-semibold">
			{m.associatedRequirements()}
			<span class="badge variant-soft-primary ml-1">
				{assessableNodesCount(treeViewNodes)}
			</span>
		</h4>
		<div class="flex items-center my-2 text-xs space-x-2 text-gray-500">
			<i class="fa-solid fa-share-nodes"></i>
			<p>{m.mappingInferenceTip()}</p>
		</div>
		<RecursiveTreeView nodes={treeViewNodes} bind:expandedNodes hover="hover:bg-initial" />
	</div>
</div>

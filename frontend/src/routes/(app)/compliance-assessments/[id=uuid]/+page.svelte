<script lang="ts">
	import { page } from '$app/stores';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import { breadcrumbObject } from '$lib/utils/stores';
	import type { TreeViewNode } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import TreeViewItemLead from './TreeViewItemLead.svelte';

	import { complianceColorMap } from './utils';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import type { Node } from './types';

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

	function transformToTreeView(nodes: Node[]) {
		return nodes.map(([id, node]) => {
			node.statusCounts = countStatus(node);
			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: { ...node, canEditRequirementAssessment },
				lead: node.status ? TreeViewItemLead : '',
				leadProps: {
					status: node.status,
					assessable: node.assessable,
					statusDisplay: node.status_display,
					statusColor: complianceColorMap[node.status]
				},
				children: node.children ? transformToTreeView(Object.entries(node.children)) : []
			};
		});
	}
	let treeViewNodes: TreeViewNode[] = transformToTreeView(Object.entries(tree));

	let expandedNodes: TreeViewNode[] = [];

	import { localStorageStore } from '@skeletonlabs/skeleton';
	import type { Writable } from 'svelte/store';

	const expandedNodesState: Writable<any> = localStorageStore('expandedNodes', expandedNodes, {
		storage: 'session'
	});

	expandedNodes = $expandedNodesState;
	$: expandedNodesState.set(expandedNodes);
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg">
		<div class="flex flex-col space-y-2 whitespace-pre-line">
			{#each Object.entries(data.compliance_assessment).filter( ([key, _]) => ['name', 'description', 'project', 'framework'].includes(key) ) as [key, value]}
				<div class="flex flex-col">
					<div class="text-sm font-medium text-gray-800 capitalize-first" data-testid={key.replaceAll('_', '-') + "-field-title"}>
						{#if key === 'urn'}
							URN
						{:else}
							{key.replace('_', ' ')}
						{/if}
					</div>
					<ul class="text-sm">
						<li class="text-gray-600 list-none" data-testid={key.replaceAll('_', '-') + "-field-value"}>
							{#if value}
								{#if Array.isArray(value)}
									<ul>
										{#each value as val}
											<li>
												{#if val.str && val.id}
													{@const itemHref = `/${
														URL_MODEL_MAP[data.urlModel]['foreignKeyFields']?.find(
															(item) => item.field === key
														)?.urlModel
													}/${val.id}`}
													<a href={itemHref} class="anchor">{val.str}</a>
												{:else}
													{value}
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
		<div class="w-full">
			<DonutChart
				s_label="compliance_assessments"
				values={compliance_assessment_donut_values.values}
			/>
		</div>
		<div class="flex flex-row space-x-2 ml-4">
			<a href={`${$page.url.pathname}/export`} class="btn variant-filled-primary h-fit"
				><i class="fa-solid fa-download mr-2" /> Export</a
			>
			{#if canEditObject}
				<a
					href={`${$page.url.pathname}/edit?next=${$page.url.pathname}`}
					class="btn variant-filled-primary h-fit"
					data-testid="edit-button"
					><i class="fa-solid fa-pen-to-square mr-2" /> Edit</a
				>
			{/if}
		</div>
	</div>

	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg">
		<h4 class="h4 font-semibold">Associated requirements</h4>
		<RecursiveTreeView nodes={treeViewNodes} bind:expandedNodes hover="hover:bg-initial" />
	</div>
</div>

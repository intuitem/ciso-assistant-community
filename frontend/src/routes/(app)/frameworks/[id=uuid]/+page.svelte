<script lang="ts">
	import type { PageData } from './$types';
	import { page } from '$app/stores';
	import type { TreeViewNode } from '@skeletonlabs/skeleton';
	import RecursiveTreeView from '$lib/components/TreeView/RecursiveTreeView.svelte';
	import TreeViewItemLead from './TreeViewItemLead.svelte';
	import TreeViewItemContent from './TreeViewItemContent.svelte';
	import { breadcrumbObject } from '$lib/utils/stores';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import * as m from '$paraglide/messages';
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let data: PageData;
	breadcrumbObject.set(data.framework);
	const tree = data.tree;

	function transformToTreeView(nodes) {
		return nodes.map(([id, node]) => {
			return {
				id: id,
				content: TreeViewItemContent,
				contentProps: node,
				// lead: TreeViewItemLead,
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
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg">
		<div class="flex flex-col space-y-2">
			{#each Object.entries(data.framework).filter(([key, _]) => key !== 'id' && key !== 'created_at') as [key, value]}
				<div class="flex flex-col">
					<div class="text-sm font-medium text-gray-800 capitalize-first">
						{#if key === 'urn'}
							{m.urn()}
						{:else}
							{m[toCamelCase(key)]() ?? key}
						{/if}
					</div>
					<ul class="text-sm">
						<li class="text-gray-600 list-none">
							{#if value}
								{#if key === 'library'}
									{@const itemHref = `/libraries/${value.urn}`}
									<a href={itemHref} class="anchor">{value.name}</a>
								{:else if key === 'scores_definition'}
									{#each Object.entries(value) as [key, definition]}
										<div>
											{definition.score}.
											{definition.name}{definition.description ? `: ${definition.description}` : ''}
										</div>
									{/each}
								{:else if key === 'implementation_groups_definition'}
									{#each Object.entries(value) as [key, definition]}
										<div>
											{definition.ref_id}. {definition.name}
										</div>
									{/each}
								{:else if Array.isArray(value)}
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
										URL_MODEL_MAP['frameworks']['foreignKeyFields']?.find(
											(item) => item.field === key
										)?.urlModel
									}/${value.id}`}
									<a href={itemHref} class="anchor">{value.str}</a>
								{:else}
									{value.str ?? value}
								{/if}
							{:else if value === 0 && key === 'min_score'}
								{value}
							{:else}
								--
							{/if}
						</li>
					</ul>
				</div>
			{/each}
		</div>
	</div>

	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg">
		<h4 class="h4 flex items-center font-semibold">
			{m.associatedRequirements()}
			<span class="badge variant-soft-primary ml-1">
				{assessableNodesCount(treeViewNodes)}
			</span>
		</h4>
		<RecursiveTreeView nodes={treeViewNodes} hover="hover:bg-initial" />
	</div>
</div>
